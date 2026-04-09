import requests
import json
import os

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

def print_result(title, result):
    print(f"\n{'='*60}")
    print(f"--- TEST: {title} ---")
    print(json.dumps(result, indent=2))

def test_text_pipeline():
    """Test standard raw WhatsApp text message"""
    url = f"{API_BASE_URL}/extract/text"
    payload = {"text": "Bhai swiggy se 450 rupaye ka pizza mangwaya cash me"}
    
    response = requests.post(url, json=payload)
    print_result("TEXT PIPELINE", response.json())

def test_audio_pipeline():
    """Test voice note upload using the root test .ogg file"""
    url = f"{API_BASE_URL}/extract/audio"
    
    # Using the audio_test.ogg from the root Fold/ directory
    audio_file_path = "audio_test.ogg"
    
    if not os.path.exists(audio_file_path):
        print(f"\n[ERROR] Audio file not found: {audio_file_path}")
        return
        
    with open(audio_file_path, "rb") as f:
        # Define multi-part form data sending as 'file'
        files = {"file": ("audio_test.ogg", f, "audio/ogg")}
        response = requests.post(url, files=files)
        
    print_result("AUDIO PIPELINE", response.json())

def test_image_pipeline():
    """Test receipt image upload using receipt3.jpg"""
    url = f"{API_BASE_URL}/extract/image"
    
    # Grab one of the receipt files from root directory
    image_file_path = "receipt3.jpg"
    
    if not os.path.exists(image_file_path):
        print(f"\n[ERROR] Image file not found: {image_file_path}")
        return
        
    with open(image_file_path, "rb") as f:
        files = {"file": ("receipt3.jpg", f, "image/jpeg")}
        response = requests.post(url, files=files)
        
    print_result("IMAGE (OCR) PIPELINE", response.json())

if __name__ == "__main__":
    print("Ensure the FastAPI server is running with 'python src/api/main.py' or 'uvicorn src.api.main:app' before testing!\n")
    
    try:
        # Check if the server is available
        requests.get("http://127.0.0.1:8000/health")
        
        test_text_pipeline()
        test_audio_pipeline()
        test_image_pipeline()
        
    except requests.exceptions.ConnectionError:
        print("[FAIL] The FastAPI server is not currently running. Please start it first!")
