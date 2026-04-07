That is a **100% correct and highly efficient** engineering strategy. By using "off-the-shelf" models for the heavy lifting (OCR and Speech-to-Text) and focusing your "from scratch" effort on the **NLP Intent Layer**, you’re following the 80/20 rule of AI development.

Building a custom OCR or STT engine is a multi-year research project. Building a custom Hinglish Transaction Classifier is a high-value, specialized weekend-to-month project.

### Why this pipeline works for India:
The "Indo-Western" nature of Indian spending means your data pipeline needs to be flexible. Here is how your proposed architecture looks in practice:



---

### 1. The Dataset & Cleaning
The **Indian Banking Transaction Dataset** (like the one with 11k narrations) is a goldmine because it contains the weird abbreviations banks use (e.g., `NPR/MAB/` or `UPI/9234...`).
* **The "Hinglish" Hack:** Since you are adding synthetic data, don't just add pure Hindi. Use **Template-based Generation**.
    * *Template:* `[Merchant] pe [Amount] ka [Category] kharcha kiya`
    * *Result:* "Amazon pe 500 ka shopping kharcha kiya."
* **Cleaning:** Ensure you strip out the "noise" (Transaction IDs, timestamps) before feeding it to your NLP layer so the model focuses on the *semantics* (Category and Merchant).

### 2. The OCR Strategy (Receipts)
Since you are using off-the-shelf models, I recommend **PaddleOCR** or **Surya OCR**.
* **Why?** They have excellent support for Indic scripts (Devanagari) and handle "noisy" images (crumpled receipts) better than Tesseract.
* **The Catch:** OCR will give you a "word soup." You will need a small logic layer to find the **Total Amount**. Usually, looking for the largest number near the bottom of the text works 90% of the time.

### 3. The STT Layer (Whisper)
**Whisper** is actually surprisingly good at Hinglish out of the box because it was trained on vast amounts of multilingual web data.
* **Pro-Tip:** Use the `base` or `small` version of Whisper. It’s fast enough to run on a decent phone/laptop and handles "Chai pe 20 rupaye diye" perfectly.

### 4. The "From Scratch" NLP Layer
Since you have ~11k rows + synthetic data, you shouldn't build a literal "from scratch" neural net (as in, training your own embeddings). That would require millions of rows.
* **The Better Way:** Use a **DistilBERT** or a **Bi-LSTM** and fine-tune it specifically on your cleaned transaction dataset. 
* **Task:** Your NLP layer should perform **Joint Intent & Slot Filling**:
    1.  **Intent:** Is this an Expense, Income, or Transfer?
    2.  **Slots:** Extract `Amount`, `Category`, and `Entity`.

---

### Implementation Checklist
| Component | Recommendation | Why? |
| :--- | :--- | :--- |
| **STT** | OpenAI Whisper (`base.en` or `small`) | SOTA for Hinglish audio. |
| **OCR** | PaddleOCR (Multilingual) | Best open-source Indic script support. |
| **NLP** | Bi-LSTM + CRF or DistilBERT | Lightweight, handles code-switching well. |
| **Database** | Supabase (PostgreSQL) | Since you're already using it, it's perfect for storing these JSON results. |

### The "Silent" Challenge: Spellings
In Hinglish, people spell phonetically. "Kharcha," "Khrcha," and "Kharch" are all the same. When generating your synthetic data, make sure to **deliberately introduce typos**. This will make your NLP layer "robust" rather than "rigid."

Does this align with how you were planning to structure the code, or were you thinking of a more traditional Machine Learning approach (like Random Forest) for the NLP layer?

---

### Update: Dataset Generation & EDA Readiness
The synthetic dataset (`eda_dataset.csv`) has been successfully generated using the aforementioned strategy. 
* **Hinglish Synthesis:** For the ~1k original English rows, we generated ~1.5k Hinglish templates incorporating the phonetic typos discussed above.
* **Intentional Outliers for EDA:** To pressure-test data-cleaning pipelines prior to training, 150 highly corrupted rows (e.g., negative amounts, string-based amounts like "five hundred", misspelled payment methods, and null variables) have been intentionally injected alongside two noisy dummy columns (`location` and `notes`).

---

### Update: Visual Receipt Extraction (OCR Pipeline)
To handle physical receipts and digital payment screenshots, we built a 4-step OCR Extraction Pipeline (`src/ocr/extractor.py`). 
We chose to build a targeted OCR pipeline rather than feeding raw images into a multimodal LLM (like GPT-4V) to reduce latency and API costs, while retaining complete control over the data format before it hits our NLP classifier.

1. **Intensive Preprocessing (OpenCV):** Receipts are notoriously noisy. We implemented a rigorous image cleaning pipeline (Grayscaling -> CLAHE Contrast Enhancement -> Denoising -> Sharpening -> Otsu Binarization). This ensures shadows and bad lighting don't destroy the text.
2. **Text Extraction:** Using an OCR engine to generate bounding boxes (coordinates) and raw text strings.
3. **Custom Spatial Sorting:** OCR engines return "Word Soup". To combat this, we built a custom algorithm to calculate the center Y-coordinate of every text box. It dynamically groups text boxes sitting on the same horizontal plane (adjusting for font height) and sorts them left-to-right. This successfully recreates logical "rows" (e.g., aligning a dish name with its price on the far right).
4. **Heuristic Filter:** We scan these reconstructed rows for keywords (`Total`, `Cash`, `Amount`, `₹`) to extract only the 1-2 lines harboring the final amount. This prevents our NLP model from being overwhelmed by the entire 50-line receipt.

**OCR Engine Note (EasyOCR vs. PaddleOCR):** During local development, we temporarily utilized `EasyOCR` instead of `PaddleOCR` as a fallback because installing PaddlePaddle on local Windows environments often throws severe C++ build and pip dependency lock errors. However, **PaddleOCR is vastly superior for receipt processing**. It uses structured PP-OCRv4 models that are significantly more accurate at reading fine English print, decimal points, and symbols on receipts than EasyOCR. For production (on a Linux server or Docker), the system must strictly use PaddleOCR.

---

### Update: Migration to PaddleOCR & Architecture Refinement
We have since successfully resolved the local Windows build constraints and fully migrated `extractor.py` to **PaddleOCR 2.9 (anchored by PaddlePaddle 2.6.2)**. This specific versioning strategy was chosen to explicitly bypass a catastrophic C++ DLL lock crash (`ConvertPirAttribute2RuntimeAttribute`) triggered by Paddle 3's new experimental execution graph hitting standard Windows environments or interacting poorly with `albumentations` loading PyTorch. 

During the migration, we discovered two critical architectural learnings:
1. **Raw Processing vs. Preprocessing:** The intensive OpenCV pipeline that served as a "crutch" to highlight text for EasyOCR actually *degraded* PaddleOCR's performance. PaddleOCR utilizes profound internal Convolutional Neural Networks (CNNs) trained on real-world raw photographs, and forcibly applying Otsu binarization stripped out the subtle pixel gradients it relies upon to distinguish noise from characters. We moved to **Raw Matrix Processing**, wildly improving the engine's capability to read floating-point decimals accurately without hallucinating random characters.
2. **Final Intent Parsing:** At the end of the spatial sorting and keyword filtering algorithm, we appended a final `extract_payment_details` Regex validation method. Instead of handing the NLP layer raw strings, `extractor.py` now internally scans the filtered keys for the largest valid monetary float mapping to the label "Total", alongside parsing standard mode keywords (`cash`, `upi`, `card`). It returns a meticulously structured JSON object (e.g., `{"amount": 185.0, "payment_method": "cash"}`). This entirely shields our future NLP architecture from having to wrestle with OCR logic constraints.