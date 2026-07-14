import cv2
import numpy as np
import torch # Import torch first to prevent WinError 127 shm.dll collision with paddle
from paddleocr import PaddleOCR
import re

class ReceiptOCR:
    def __init__(self, lang='en'):
        """
        Initialize the OCR engine using PaddleOCR.
        PaddleOCR is used because it has excellent accuracy for
        multi-language text (English + Hindi) found on Indian receipts.
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
        # PaddleOCR expects a 3-channel BGR array
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

        OCR engines return text fragments in random order. This method
        groups fragments that are on the same horizontal line (by Y position)
        and sorts them left-to-right (by X position) to rebuild readable lines.

        Steps:
            1. Compute center-Y and height for each text box.
            2. Group boxes whose center-Y values are close together (same row).
            3. Sort each group left-to-right by X position.
            4. Join each group into a single line string.
        """
        if not extracted_data:
            return []

        # Calculate position info for each text fragment
        for item in extracted_data:
            ys = [pt[1] for pt in item["bbox"]]
            xs = [pt[0] for pt in item["bbox"]]
            item["center_y"] = sum(ys) / len(ys)
            item["min_x"] = min(xs)
            item["height"] = max(ys) - min(ys)

        # Dynamic threshold: 50% of average font height
        # This prevents merging separate rows while correctly grouping
        # fragments that belong to the same row but jitter vertically
        avg_height = sum(d["height"] for d in extracted_data) / len(extracted_data)
        dynamic_thresh = max(y_threshold, int(avg_height * 0.5))

        # Sort all fragments top-to-bottom
        extracted_data.sort(key=lambda d: d["center_y"])

        # Group fragments into lines based on Y proximity
        lines = []
        current_line = [extracted_data[0]]
        current_y = extracted_data[0]["center_y"]

        for item in extracted_data[1:]:
            if abs(item["center_y"] - current_y) <= dynamic_thresh:
                # Same line — add to current group
                current_line.append(item)
                current_y = sum(i["center_y"] for i in current_line) / len(current_line)
            else:
                # New line — save current group and start a new one
                lines.append(current_line)
                current_line = [item]
                current_y = item["center_y"]
        lines.append(current_line)

        # Sort each line left-to-right and join into strings
        rebuilt = []
        for line in lines:
            line.sort(key=lambda d: d["min_x"])
            rebuilt.append(" ".join(item["text"] for item in line))
        return rebuilt

    # ─── End-to-End Pipeline ────────────────────────────────────────────

    def process_receipt(self, image_path: str, use_preprocessing: bool = True) -> dict:
        """
        Run the full OCR pipeline on an image.

        Returns:
            dict with:
                - all_lines: List of reconstructed text lines from the image
                - raw_text: All lines joined into a single string
        """
        print(f"[OCR] Processing: {image_path}  (preprocess={use_preprocessing})")

        if use_preprocessing:
            img = self.preprocess(image_path)
        else:
            img = cv2.imread(image_path)

        raw_data = self.extract_raw_text(img)
        all_lines = self.sort_spatially(raw_data)

        return {
            "all_lines": all_lines,
            "raw_text": " ".join(all_lines),
        }


# ═══════════════════════════════════════════════════════════════════════
# Test Runner
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import json
    IMG = "../../receipt7.jpg"

    ocr = ReceiptOCR()
    result = ocr.process_receipt(IMG, use_preprocessing=False)

    print("\\n========== RECONSTRUCTED LINES ==========")
    for line in result["all_lines"]:
        print(f"  >> {line}")

    print("\\n========== RAW TEXT ==========")
    print(result["raw_text"])
