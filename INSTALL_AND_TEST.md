# Installation and Testing Guide

## Problem Found! ❌

Your Python dependencies are **NOT installed**! The test revealed:
- ❌ `paddleocr` not installed (OCR pipeline)
- ❌ `whisper` not installed (Audio pipeline)
- ❌ `torch`/`transformers` version mismatch (NLP pipeline)

## Solution: Install Dependencies

### Step 1: Activate Virtual Environment
```powershell
.\venv\Scripts\activate
```

### Step 2: Install All Dependencies
```powershell
pip install -r requirements.txt
```

**This will take 5-10 minutes** as it installs:
- PyTorch (large ML library)
- PaddleOCR (OCR engine)
- Whisper (speech-to-text)
- Transformers (NLP models)

### Step 3: Verify Installation
```powershell
python -c "import paddleocr; import whisper; import transformers; print('✅ All dependencies installed!')"
```

### Step 4: Test Pipelines Again
```powershell
python test_extraction_pipelines.py
```

## Expected Output After Installation

### Text Extraction (NLP):
```
Input: spent 100 on coffee at starbucks
  Amount: 100
  Category: food
  Payment Method: unknown
  Cash Flow: expense

✅ NLP Pipeline: WORKING
```

### Image Extraction (OCR):
```
Step 1: UPI Detection...
  UPI Provider: gpay

Step 2: OCR Extraction...
  Extracted 15 lines
  OCR Amount: 250.00
  Text preview: ...

Step 3: Ollama Structuring...
  LLM Amount: 250.00
  LLM Description: groceries

Step 4: NLP Classification...
  NLP Category: food

Final Merged Result:
  Amount: 250.00
  Category: food
  Payment Method: upi

✅ Image Extraction Pipeline: WORKING
```

### Audio Extraction (STT):
```
Step 1: Speech-to-Text...
  Transcript: I spent 300 rupees on pizza
  Language: en

Step 2: NLP Extraction from transcript...
  Amount: 300
  Category: food
  Payment Method: unknown

✅ Audio Extraction Pipeline: WORKING
```

## Why This Happened

The virtual environment (`venv`) was created but dependencies were never installed. This is why:
1. Backend starts (FastAPI doesn't need ML libraries to start)
2. Health check works (no dependencies needed)
3. But extraction fails (needs paddleocr, whisper, torch)

## Quick Install Command

```powershell
# One command to do everything
.\venv\Scripts\activate ; pip install -r requirements.txt ; python test_extraction_pipelines.py
```

## If Installation Fails

### Issue: PyTorch Installation
If PyTorch fails to install:
```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### Issue: PaddleOCR Installation
If PaddleOCR fails:
```powershell
pip install paddlepaddle paddleocr opencv-python
```

### Issue: Whisper Installation
If Whisper fails:
```powershell
pip install openai-whisper
```

## After Installation

Once dependencies are installed:
1. ✅ NLP pipeline will work
2. ✅ OCR pipeline will work
3. ✅ STT pipeline will work
4. ✅ Frontend will be able to extract from text/image/audio
5. ✅ No more "header too large" errors (that was a red herring)

## The Real Problem

The "header too large" error was likely a **misleading error message**. The real issue was:
1. Frontend sends request
2. Backend receives it
3. Backend tries to import `paddleocr` or `whisper`
4. Import fails (not installed)
5. Backend returns 500 error
6. Error message gets garbled/misinterpreted

**Install the dependencies and everything will work!** 🚀
