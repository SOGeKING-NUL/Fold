import cv2
import numpy as np
from paddleocr import PaddleOCR
import re


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
        triggers = re.compile(
            r'(?:total|amount|paid|cash|card|upi|net|inr|rs\.?|stl?|tl|₹|grand|arand)',
            re.IGNORECASE
        )
        has_amount = re.compile(r'\d{2,}')  # at least a 2-digit number

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

    def extract_payment_details(self, key_lines: list) -> dict:
        """
        Parses the filtered key lines to extract the final payment amount
        and the mode of payment (Cash, Card, UPI, etc.)
        """
        amount = None
        payment_method = "unknown"
        amounts = []
        
        for line in key_lines:
            # Extract decimals like 185.00, 1,200.50, etc.
            matches = re.findall(r'\b\d{1,3}(?:,\d{3})*(?:\.\d{2})\b|\b\d+\.\d{2}\b', line)
            if not matches:
                matches = re.findall(r'\b\d+\.\d+\b', line)
            
            for m in matches:
                val = float(m.replace(',', ''))
                if val > 0:
                    amounts.append(val)
            
            # Extract Payment Mode
            lower_line = line.lower()
            modes = ["cash", "card", "upi", "visa", "mastercard", "gpay", "paytm", "amex"]
            for mode in modes:
                if mode in lower_line:
                    payment_method = mode

        # The Grand Total is typically the largest valid monetary value in the heavily filtered key_lines
        if amounts:
            amount = max(amounts)

        return {"amount": amount, "payment_method": payment_method}

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
        parsed = self.extract_payment_details(key_lines)

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
    IMG = "../../receipt2.jpg"

    ocr = ReceiptOCR()

    # We only run the RAW image mode now since it provides vastly superior accuracy for PaddleOCR
    result = ocr.process_receipt(IMG, use_preprocessing=False)

    print("\n========== RAW IMAGE — KEY LINES ==========")
    for line in result["key_lines"]:
        print(f"  >> {line}")

    print("\n========== FINAL EXTRACTED JSON ==========")
    print(json.dumps(result["parsed"], indent=4))
