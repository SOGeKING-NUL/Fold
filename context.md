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

### Example: How the Heuristic Filter Handles Ambiguous Lines
**Input RAW Key Line:** 
`>> Total : 4.00 1450.00`

In this example (from `receipt5.jpg`), the word `Total` is structurally adjacent to both the quantity (`4.00`) and the final price (`1450.00`). 
Instead of a simple regex that grabs the *first* number it sees (which would fail by extracting `4.00`), our `extract_payment_details` regex strictly extracts *every* valid float on lines containing `Total/Payable`. It generates an array of candidates: `[4.0, 1450.0]`. 

Because it is evaluating a designated "Total" line, it applies `max([4.0, 1450.0])`, perfectly bypassing quantities and discounts to output the true JSON:
{
    "amount": 1450.0,
    "payment_method": "unknown"
}
```

### Payment Method Normalization (ENUMs)
Because UPI screenshots contain diverse merchant tools (BHIM, PhonePe, GPay, Paytm, Cred) and physical receipts mention specific card networks (Visa, Mastercard, Amex), the `extract_payment_details` module normalizes these downstream. It strictly maps any found payment application to one of three final `ENUM` states: 
* `"upi"`
* `"card"`
* `"cash"`
* `"unknown"` (Fallback)

---

### Update: Voice Note Extraction (STT Pipeline)
To handle spoken Hinglish voice notes (the second major input channel alongside receipt images), we built a Speech-to-Text pipeline (`src/stt/transcriber.py`) using **OpenAI Whisper** running locally.

#### Why Whisper?
Whisper was trained on 680,000 hours of multilingual audio data scraped from the web. Unlike Google STT or AWS Transcribe, which require explicit language selection and struggle with code-switching, Whisper natively handles **Hinglish** — the fluid mix of Hindi and English that Indian users default to when speaking about money (e.g., "Swiggy se do sau pachaas rupaye ka order kiya, UPI se pay kiya").

#### Architecture (3 Steps)
The module mirrors the OCR extractor's structure exactly:

1. **Transcription (Whisper `base` model):** The audio file (.ogg, .wav, .mp3, etc.) is decoded via FFmpeg and passed to Whisper's encoder-decoder transformer. We inject a **domain prompt** — a pre-written Hinglish banking sentence — into Whisper's `initial_prompt` parameter. This is a critical engineering trick: it anchors the model's decoder latent space to our financial vocabulary, preventing it from force-translating Hindi words into English or hallucinating irrelevant text. We set `language="hi"` to keep the decoder in Hindi mode (which naturally preserves Hinglish code-switching).

#### Output Format
The `process_audio()` method simply returns a dict with the raw transcript:
```json
{
    "transcript": "Spent 3000 rupees on shopping."
}
```
*Note: We deliberately decided against attempting complex regex amount/payment extraction within the STT module itself. Because the downstream Artificial NLP Layer will be explicitly trained to parse intent and extract entity slots from Hinglish sentences, we only require Whisper to deliver an accurate string, delegating all intelligence to the NLP classifier.*

#### Dependencies & Environment Notes
* **openai-whisper** (installed via `pip install openai-whisper`). This is the *local* model, not the OpenAI API — no API key needed, no network calls during inference.
* **FFmpeg 8.1** (installed via `winget install Gyan.FFmpeg`). Required by Whisper to decode audio containers (OGG/Opus from WhatsApp, M4A from iPhone voice memos, etc.) into raw PCM waveforms. Must be on the system PATH.
* **torch** (pulled automatically by whisper). We are using the CPU-only variant (`fp16=False` in transcribe config) to avoid CUDA dependency on development machines.
* **Model size:** Using `base` (139 MB download, ~1 GB RAM at inference). Can be upgraded to `small` (461 MB) for higher accuracy if hardware allows.

---

### Update: Hybrid Payment Tracking (NLP + UX)
Extracting the `payment_method` exclusively from free-form WhatsApp voice notes introduces a vulnerability. Users often say "Zomato pe 500 ka kharcha kiya" but completely omit *how* they paid (UPI, cash, etc.).

Instead of blindly defaulting to "unknown" and corrupting the financial database, we have agreed on a **Hybrid Architecture (NLP layer + Chatbot UX)**:

1. **Attempt NLP Extraction First:** Deep inside the NLP Inference layer, we will run a specialized Regex/Dictionary matcher against the transcript. It scans for explicit mentions:
   * **UPI:** `"upi", "gpay", "paytm", "phonepe", "bhim", "cred"`
   * **Card:** `"card", "visa", "mastercard", "amex"`
   * **Cash:** `"cash", "naqad", "nakd"`
2. **Interactive WhatsApp Fallback:** If the NLP layer returns `payment_method: null` (meaning the user didn't explicitly vocalize it), the system does **not** fail. Instead, the backend will trigger a specific WhatsApp Interactive Message containing three UI buttons: `[ 💵 Cash ]`, `[ 📱 UPI ]`, `[ 💳 Card ]`.
3. **Database Finalization:** Once the user taps the button, the webhook receives the payload and completes the transaction row in the database.

This strategy guarantees 100% data completion while maintaining a frictionless UX.

---

### Update: Framework Decision (PyTorch vs. TensorFlow)
For the Deep Learning NLP Layer, we are utilizing **PyTorch** via HuggingFace Transformers, deliberately avoiding TensorFlow. The core reasons are:

1. **Ecosystem Dominance:** In modern NLP (especially post-2022 LLMs and Transformer variants), PyTorch has become the undisputed industry standard. Over 90% of state-of-the-art models released on HuggingFace are natively built in PyTorch. Finding TensorFlow implementations of modern Indic-language or Hinglish optimized sequence classifiers is often difficult and prone to bugs.
2. **Environment Synchronization:** Our STT layer (OpenAI Whisper) natively relies on the `torch` backend. By selecting PyTorch for the NLP DistilBERT classifier, we prevent monolithic environment bloat. If we introduced TensorFlow, the production deployed server would be forced to house *both* massive 2GB+ deep learning frameworks simultaneously, catastrophically increasing RAM footprint and cold-start latency.
3. **Pythonic Extensibility:** PyTorch's dynamic computational graph structure (`Eager Execution`) feels like standard Python, making it significantly easier to debug model gradients or tweak the internal loss functions during Colab fine-tuning. TensorFlow's static graph architecture (`tf.function` decorators), while great for heavy scale, introduces unnecessary friction for a rapid prototyping stealth financial application.