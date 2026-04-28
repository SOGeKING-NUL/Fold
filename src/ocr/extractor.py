import cv2
import numpy as np
from paddleocr import PaddleOCR
import re

from ocr.amount_plausibility import (
    _is_year_in_date_context,
    extract_payment_instrument_from_lines,
    is_likely_identifier_number_in_line,
    is_likely_bank_last4_in_line,
    plausible_inr_amount,
)
from ocr.cash_flow import detect_cash_flow_from_text


class ReceiptOCR:
    def __init__(self, lang='en'):
        """
        Initialize the OCR engine using PaddleOCR for superior accuracy.
        """
        self.reader = PaddleOCR(use_angle_cls=True, lang=lang)

    # ─── Image Preprocessing ────────────────────────────────────────────

    def _upscale(self, img: np.ndarray, target_height: int = 1500) -> np.ndarray:
        """Upscale small images so OCR can see fine text clearly."""
        h, w = img.shape[:2]
        if h >= target_height:
            return img
        scale = target_height / h
        return cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    def _enhance_contrast(self, gray: np.ndarray) -> np.ndarray:
        """
        Use CLAHE (Contrast Limited Adaptive Histogram Equalization)
        to boost text visibility in dark or unevenly-lit receipt photos.
        """
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        return clahe.apply(gray)

    def _denoise(self, gray: np.ndarray) -> np.ndarray:
        """Remove noise while keeping edges sharp."""
        return cv2.fastNlMeansDenoising(gray, h=12, templateWindowSize=7, searchWindowSize=21)

    def _sharpen(self, gray: np.ndarray) -> np.ndarray:
        """Apply a mild sharpening kernel to crisp up blurry text."""
        kernel = np.array([[0, -1, 0],
                           [-1,  5, -1],
                           [0, -1, 0]])
        return cv2.filter2D(gray, -1, kernel)

    def _binarize(self, gray: np.ndarray) -> np.ndarray:
        """Otsu binarization — works well after CLAHE has normalized contrast."""
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    def preprocess(self, image_path: str) -> np.ndarray:
        """
        Full preprocessing pipeline for receipt images:
        Upscale → Grayscale → CLAHE → Denoise → Sharpen → Binarize
        """
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Could not read image: {image_path}")

        img = self._upscale(img)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = self._enhance_contrast(gray)
        gray = self._denoise(gray)
        gray = self._sharpen(gray)
        binary = self._binarize(gray)
        return binary

    # ─── OCR Extraction ─────────────────────────────────────────────────

    def extract_raw_text(self, image: np.ndarray) -> list:
        """Pass an image matrix to PaddleOCR and return bounding-box data."""
        # PaddleOCR expects a 3-channel BGR array.
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        results = self.reader.ocr(image, cls=True)
        
        extracted = []
        if results and results[0]:
            for line in results[0]:
                bbox = line[0]
                text = line[1][0]
                conf = line[1][1]
                extracted.append({"bbox": bbox, "text": text, "confidence": conf})
        return extracted

    # ─── Spatial Sorting ────────────────────────────────────────────────

    def sort_spatially(self, extracted_data: list, y_threshold: int = 15) -> list:
        """
        Rebuild receipt rows from scattered OCR bounding boxes.
        1. Compute center-Y and height for each box.
        2. Set a dynamic threshold based on text height.
        3. Group boxes whose center-Y values align.
        4. Sort each group left-to-right by X.
        5. Join into a single line string.
        """
        if not extracted_data:
            return []

        for item in extracted_data:
            ys = [pt[1] for pt in item["bbox"]]
            xs = [pt[0] for pt in item["bbox"]]
            item["center_y"] = sum(ys) / len(ys)
            item["min_x"] = min(xs)
            item["height"] = max(ys) - min(ys)

        # Dynamic threshold: 50% of the average font height, ensuring we don't merge separate rows
        # but correctly merge boxes belonging to the same row that jitter up and down.
        avg_height = sum(d["height"] for d in extracted_data) / len(extracted_data)
        dynamic_thresh = max(y_threshold, int(avg_height * 0.5))

        extracted_data.sort(key=lambda d: d["center_y"])

        lines = []
        current_line = [extracted_data[0]]
        current_y = extracted_data[0]["center_y"]

        for item in extracted_data[1:]:
            if abs(item["center_y"] - current_y) <= dynamic_thresh:
                current_line.append(item)
                # Update running average of the line's Y center
                current_y = sum(i["center_y"] for i in current_line) / len(current_line)
            else:
                lines.append(current_line)
                current_line = [item]
                current_y = item["center_y"]
        lines.append(current_line)

        rebuilt = []
        for line in lines:
            line.sort(key=lambda d: d["min_x"])
            rebuilt.append(" ".join(item["text"] for item in line))
        return rebuilt

    # ─── Heuristic Filtering ────────────────────────────────────────────

    def filter_key_lines(self, lines: list) -> list:
        """
        Find the lines most likely to contain the final transaction amount.
        Handles cases where OCR splits the label and the amount onto adjacent lines.
        """
        # Use word boundaries for short or ambiguous abbreviations to prevent them from matching inside words (e.g. "Storm" matching "St")
        triggers = re.compile(
            r'\b(?:total|amount|paid|cash|card|upi|net|inr|rs\.?|st|stl|tl|grand|arand)\b|₹|total:|total\s*',
            re.IGNORECASE
        )
        # Match strict decimals OR integers explicitly preceded by a currency marker or 'paid'
        has_amount = re.compile(r'\d{2,}\.\d{2}|(?:\b(?:rs\.?|inr|r)|₹)\s*\d{1,}', re.IGNORECASE)

        key = []
        n = len(lines)
        for i, line in enumerate(lines):
            has_trigger = triggers.search(line)
            has_num = has_amount.search(line)

            # Case 1: Perfect line containing both
            if has_trigger and has_num:
                key.append(line)
            # Case 2: Label is here, but number got pushed to the line above/below
            elif has_trigger and not has_num:
                context = line
                # Look one line ahead
                if i + 1 < n and has_amount.search(lines[i+1]):
                    context = line + " " + lines[i+1]
                # Look one line behind (if the amount bounced upwards into the previous margin)
                elif i - 1 >= 0 and has_amount.search(lines[i-1]) and not triggers.search(lines[i-1]):
                    context = line + " " + lines[i-1]

                if has_amount.search(context) and context != line:
                    key.append(context)

        # Deduplicate, preserving order
        unique_keys = []
        for k in key:
            if k not in unique_keys:
                unique_keys.append(k)

        return unique_keys

    # ─── Data Extraction ────────────────────────────────────────────────

    # Provider keyword → canonical slug (same as NLP layer for consistency)
    _UPI_PROVIDER_MAP: dict[str, str] = {
        "gpay": "gpay", "google pay": "gpay", "g pay": "gpay",
        "phonepe": "phonepe", "phone pe": "phonepe",
        "paytm": "paytm", "bhim": "bhim", "cred": "cred",
        "bharatpe": "bharatpe", "amazon pay": "amazonpay",
        "amazonpay": "amazonpay", "freecharge": "freecharge",
        "mobikwik": "mobikwik",
        "slice": "slice", "jupiter": "jupiter", "fi": "fi", "niyo": "niyo",
    }

    def extract_payment_details(self, key_lines: list, all_lines: list | None = None) -> dict:
        """
        Parses the filtered key lines to extract the final payment amount
        by strictly associating it with explicit finality keywords instead of max().
        Also scans all OCR lines for a UPI provider name.
        """
        final_amount = None
        payment_method = "unknown"
        payment_provider: str | None = None

        total_keywords = [
            "grand total",
            "total",
            "payable",
            "cash",
            "net amount",
            "amount paid",
            "balance",
            "net",
            "paid",
            "sent",
            "successful",
            "completed",  # GPay / many apps: "Completed" on success screen
        ]

        found_amounts: list[float] = []
        all_fallback_amounts: list[float] = []

        upi_keywords = ["upi", "gpay", "google pay", "paytm", "bhim", "phonepe", "phone pe", "bharatpe", "cred"]
        card_keywords = ["card", "visa", "mastercard", "amex"]
        cash_keywords = ["cash"]

        scan_lines = list(key_lines)
        if all_lines:
            scan_lines = list(all_lines)

        for line in scan_lines:
            lower_line = line.lower()
            for kw, prov in self._UPI_PROVIDER_MAP.items():
                if kw in lower_line and payment_provider is None:
                    payment_provider = prov

        # Scan both key lines and full OCR lines so we do not miss a hero amount when
        # filter_key_lines drops a bare "100" row; still drop bank last-4 (e.g. "HDFC Bank 1751").
        seen_line: set[str] = set()
        amount_lines: list[str] = []
        for L in list(key_lines or []) + list(all_lines or []):
            if L not in seen_line:
                seen_line.add(L)
                amount_lines.append(L)

        for line in amount_lines:
            lower_line = line.lower()

            for kw in upi_keywords:
                if kw in lower_line:
                    payment_method = "upi"
            for kw in card_keywords:
                if kw in lower_line:
                    payment_method = "card"
            for kw in cash_keywords:
                if kw in lower_line:
                    payment_method = "cash"

            matches = re.findall(
                r'(?<!\d)\d{1,3}(?:,\d{3})*(?:\.\d{2})\b|(?<!\d)\d+\.\d{2}\b', line
            )

            if not matches:
                curr_matches = re.findall(
                    r'(?:\b(?:rs\.?|inr|r)|[₹$t?])\s*(\d{1,3}(?:,\d{3})*|\d+)', lower_line
                )
                matches = curr_matches
            # GPay etc. often drop the rupee symbol; pick 2–4 digit amounts here, then drop last-4.
            if not matches:
                matches = re.findall(r'(?<![\d.])(\d{2,4})(?![\d.])', line)

            line_amounts: list[float] = []
            for m in matches:
                val = float(str(m).replace(",", ""))
                if not plausible_inr_amount(val):
                    continue
                if is_likely_bank_last4_in_line(line, val):
                    continue
                if is_likely_identifier_number_in_line(line, val):
                    continue
                if _is_year_in_date_context(line, val):
                    continue
                line_amounts.append(val)
                all_fallback_amounts.append(val)

            if not line_amounts:
                continue

            is_total_line = any(kw in lower_line for kw in total_keywords)
            if is_total_line:
                found_amounts.append(max(line_amounts))

        if found_amounts:
            final_amount = max(found_amounts)
        elif all_fallback_amounts:
            final_amount = max(all_fallback_amounts)

        if payment_provider and payment_method == "unknown":
            payment_method = "upi"

        flow_blob = " ".join(scan_lines) if scan_lines else ""
        cash_flow = detect_cash_flow_from_text(flow_blob)

        inst_last4, inst_hint = extract_payment_instrument_from_lines(amount_lines)

        return {
            "amount": final_amount,
            "payment_method": payment_method,
            "payment_provider": payment_provider,
            "cash_flow": cash_flow,
            "instrument_last4": inst_last4,
            "instrument_institution_hint": inst_hint,
        }

    # ─── End-to-End Pipeline ────────────────────────────────────────────

    def process_receipt(self, image_path: str, use_preprocessing: bool = True) -> dict:
        """
        Run the full pipeline on a receipt image.
        Returns all reconstructed lines and the filtered key lines.
        """
        print(f"[*] Processing: {image_path}  (preprocess={use_preprocessing})")

        if use_preprocessing:
            img = self.preprocess(image_path)
        else:
            img = cv2.imread(image_path)

        raw_data = self.extract_raw_text(img)
        all_lines = self.sort_spatially(raw_data)
        key_lines = self.filter_key_lines(all_lines)
        parsed = self.extract_payment_details(key_lines, all_lines=all_lines)

        return {
            "all_lines": all_lines, 
            "key_lines": key_lines,
            "parsed": parsed
        }


# ═══════════════════════════════════════════════════════════════════════
# Test Runner
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import json
    IMG = "../../receipt7.jpg"

    ocr = ReceiptOCR()

    # We only run the RAW image mode now since it provides vastly superior accuracy for PaddleOCR
    result = ocr.process_receipt(IMG, use_preprocessing=False)

    print("\n========== RAW IMAGE — KEY LINES ==========")
    for line in result["key_lines"]:
        print(f"  >> {line}")

    print("\n========== FINAL EXTRACTED JSON ==========")
    print(json.dumps(result["parsed"], indent=4))
