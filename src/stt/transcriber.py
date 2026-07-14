"""
Speech-to-Text (STT) Transcription Module
==========================================
Converts voice notes into text using Sarvam AI's speech-to-text API.

Architecture Summary:
    1. Reads audio file.
    2. Sends audio to Sarvam AI (saaras:v3 model) for highly accurate 
       Indian-dialect (Hinglish/Hindi/English) transcription.
    3. Returns the raw transcript string.

Dependencies:
    - requests

Usage:
    from stt.transcriber import transcribe_audio
    transcript = transcribe_audio("voice_note.ogg", api_key="your_sarvam_key")
    print(transcript)
"""

import logging
import os
import requests

_logger = logging.getLogger(__name__)

def transcribe_audio(audio_path: str, api_key: str) -> str:
    """
    Transcribe an audio file to text via Sarvam AI API.

    Args:
        audio_path: Path to the audio file.
        api_key: Sarvam AI API subscription key.

    Returns:
        The raw transcript string.
    """
    if not api_key:
        raise ValueError("Sarvam API key is required")

    _logger.info(f"[STT] Transcribing via Sarvam: {audio_path}")

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    url = "https://api.sarvam.ai/speech-to-text"
    headers = {
        "api-subscription-key": api_key
    }

    with open(audio_path, "rb") as f:
        files = {
            "file": (os.path.basename(audio_path), f, "audio/mpeg")
        }
        data = {
            "model": "saaras:v3",
            "language_code": "hi-IN",
            "mode": "translit"
        }
        
        response = requests.post(url, headers=headers, files=files, data=data, timeout=60)
    
    response.raise_for_status()
    
    result_json = response.json()
    transcript = result_json.get("transcript", "").strip()
    
    _logger.info(f"[STT] Transcript: {transcript}")
    return transcript

# ═══════════════════════════════════════════════════════════════════════
# Test Runner
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    load_dotenv("../../.env")
    test_key = os.getenv("SARVAM_API_KEY")

    if not test_key:
        print("Error: SARVAM_API_KEY not found in .env")
        sys.exit(1)

    AUDIO = sys.argv[1] if len(sys.argv) > 1 else "../../audio_test.ogg"

    try:
        res = transcribe_audio(AUDIO, api_key=test_key)
        print("\\n========== FINAL OUTPUT ==========")
        print(res)
    except Exception as e:
        print(f"Error: {e}")
