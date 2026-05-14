"""
Test Extraction Pipelines
==========================
Tests the actual NLP, OCR, and STT pipelines with real data.
"""
import sys
import os

# Add src to path
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

print("="*80)
print("🧪 TESTING EXTRACTION PIPELINES")
print("="*80)
print()

# Test 1: Text Extraction (NLP)
print("Test 1: Text Extraction (NLP Pipeline)")
print("-" * 80)
try:
    from nlp.inference import TransactionExtractor
    
    nlp = TransactionExtractor()
    test_texts = [
        "spent 100 on coffee at starbucks",
        "paid 500 rupees for groceries",
        "received 2000 salary",
        "spent 300 on pizza"
    ]
    
    for text in test_texts:
        result = nlp.extract(text)
        print(f"\nInput: {text}")
        print(f"  Amount: {result.get('amount')}")
        print(f"  Category: {result.get('category')}")
        print(f"  Payment Method: {result.get('payment_method')}")
        print(f"  Cash Flow: {result.get('cash_flow')}")
    
    print("\n✅ NLP Pipeline: WORKING")
except Exception as e:
    print(f"\n❌ NLP Pipeline FAILED: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 2: Image Extraction (OCR + Ollama)
print("Test 2: Image Extraction (OCR Pipeline)")
print("-" * 80)
image_path = "assests/demo4.jpg"
if os.path.exists(image_path):
    try:
        from ocr.extractor import ReceiptOCR
        from ocr.upi_detector import UPIAppDetector
        from api.config import get_settings
        
        settings = get_settings()
        
        # Step 1: UPI Detection
        print("\nStep 1: UPI Detection...")
        visual_provider = None
        try:
            if settings.roboflow_api_key:
                detector = UPIAppDetector(
                    api_key=settings.roboflow_api_key,
                    model_id=settings.roboflow_upi_model_id,
                )
                visual_provider = detector.detect(image_path)
                print(f"  UPI Provider: {visual_provider or 'None detected'}")
        except Exception as e:
            print(f"  UPI Detection failed: {e}")
        
        # Step 2: OCR
        print("\nStep 2: OCR Extraction...")
        ocr = ReceiptOCR()
        ocr_result = ocr.process_receipt(image_path, use_preprocessing=False)
        all_text = " ".join(ocr_result.get("all_lines", []))
        ocr_parsed = ocr_result.get("parsed", {})
        
        print(f"  Extracted {len(ocr_result.get('all_lines', []))} lines")
        print(f"  OCR Amount: {ocr_parsed.get('amount')}")
        print(f"  OCR Payment Method: {ocr_parsed.get('payment_method')}")
        print(f"  Text preview: {all_text[:100]}...")
        
        # Step 3: Ollama Structuring (if enabled)
        print("\nStep 3: Ollama Structuring...")
        llm_result = {}
        if settings.ollama_enabled:
            try:
                from nlp.ollama_structurer import OllamaStructurer
                
                ollama = OllamaStructurer(
                    base_url=settings.ollama_base_url,
                    model=settings.ollama_model,
                    timeout_seconds=settings.ollama_timeout_seconds,
                )
                llm_result = ollama.structure_from_ocr(
                    raw_text=all_text,
                    text_source="receipt_ocr",
                    hints={
                        "visual_provider": visual_provider,
                        "ocr_amount": ocr_parsed.get("amount"),
                    },
                )
                print(f"  LLM Amount: {llm_result.get('amount')}")
                print(f"  LLM Description: {llm_result.get('description')}")
                print(f"  LLM Payment Method: {llm_result.get('payment_method')}")
            except Exception as e:
                print(f"  Ollama failed: {e}")
        else:
            print("  Ollama disabled in config")
        
        # Step 4: NLP Classification
        print("\nStep 4: NLP Classification...")
        from nlp.inference import TransactionExtractor
        
        nlp = TransactionExtractor()
        nlp_result = nlp.extract(all_text or "expense")
        
        print(f"  NLP Category: {nlp_result.get('category')}")
        print(f"  NLP Amount: {nlp_result.get('amount')}")
        
        # Final merged result
        print("\nFinal Merged Result:")
        final_amount = llm_result.get("amount") or ocr_parsed.get("amount") or nlp_result.get("amount")
        final_payment = llm_result.get("payment_method") or ocr_parsed.get("payment_method") or nlp_result.get("payment_method")
        final_category = nlp_result.get("category")
        
        print(f"  Amount: {final_amount}")
        print(f"  Category: {final_category}")
        print(f"  Payment Method: {final_payment}")
        
        if final_amount:
            print("\n✅ Image Extraction Pipeline: WORKING")
        else:
            print("\n⚠️  Image Extraction Pipeline: No amount extracted")
            
    except Exception as e:
        print(f"\n❌ Image Extraction Pipeline FAILED: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"❌ Image file not found: {image_path}")

print()

# Test 3: Audio Extraction (STT + NLP)
print("Test 3: Audio Extraction (STT Pipeline)")
print("-" * 80)
audio_path = "assests/audio_demo2.ogg"
if os.path.exists(audio_path):
    try:
        from stt.transcriber import VoiceTranscriber
        from nlp.inference import TransactionExtractor
        
        # Step 1: Transcribe
        print("\nStep 1: Speech-to-Text...")
        stt = VoiceTranscriber(model_size="small")
        stt_result = stt.process_audio(audio_path)
        transcript = stt_result["transcript"]
        
        print(f"  Transcript: {transcript}")
        print(f"  Language: {stt_result.get('language')}")
        
        # Step 2: Extract from transcript
        print("\nStep 2: NLP Extraction from transcript...")
        nlp = TransactionExtractor()
        extracted = nlp.extract(transcript)
        
        print(f"  Amount: {extracted.get('amount')}")
        print(f"  Category: {extracted.get('category')}")
        print(f"  Payment Method: {extracted.get('payment_method')}")
        
        if extracted.get('amount'):
            print("\n✅ Audio Extraction Pipeline: WORKING")
        else:
            print("\n⚠️  Audio Extraction Pipeline: No amount extracted")
            print(f"     (Transcript was: {transcript})")
            
    except Exception as e:
        print(f"\n❌ Audio Extraction Pipeline FAILED: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"❌ Audio file not found: {audio_path}")

print()
print("="*80)
print("📋 PIPELINE TEST SUMMARY")
print("="*80)
print()
print("Check the results above to see which pipelines are working.")
print("If any pipeline failed, check the error messages for details.")
print()
