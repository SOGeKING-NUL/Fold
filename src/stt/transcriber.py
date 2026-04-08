"""
Speech-to-Text (STT) Transcription Module
==========================================
Converts voice notes into structured transaction data using OpenAI Whisper.

Architecture Summary:
    1. Load Whisper model (default: "base") — small footprint, good Hinglish accuracy.
    2. Transcribe audio with an injected Hinglish banking prompt to bias the decoder.
    3. Parse the raw transcript using regex to extract amount and payment method.
    4. Return a JSON-compatible dict identical to the OCR extractor output:
       {"amount": float, "payment_method": str}

Dependencies:
    - openai-whisper  (the local model, NOT the API)
    - ffmpeg          (must be on system PATH for audio decoding)
    - torch           (installed automatically with whisper)

Usage:
    from transcriber import VoiceTranscriber
    stt = VoiceTranscriber()
    result = stt.process_audio("voice_note.ogg")
    print(result)
    # {"transcript": "...", "parsed": {"amount": 500.0, "payment_method": "upi"}}
"""

import re
import whisper


class VoiceTranscriber:
    """
    Wraps OpenAI Whisper to transcribe Hinglish voice notes
    and extract structured financial data from the transcript.
    """

    # ─── Hinglish Domain Prompt ─────────────────────────────────────────
    # Whisper uses this as a "style anchor" during decoding.
    # By feeding it a realistic Hinglish banking sentence, we bias
    # the model to preserve code-switched words (e.g., "rupaye", "kharcha")
    # instead of force-translating them into pure English.
    DOMAIN_PROMPT = (
        "Amazon pe 500 rupaye ka shopping kharcha kiya, UPI se pay kiya. "
        "Zomato pe 250 rupaye kharch kiye cash se. "
        "Electricity bill 1200 rupaye card se pay kiya."
    )

    def __init__(self, model_size: str = "small"):
        """
        Initialize the Whisper model.

        Args:
            model_size: One of "tiny", "base", "small", "medium", "large".
                        "small" is the recommended minimum for solid Hinglish.
        """
        print(f"[STT] Loading Whisper model: {model_size}")
        self.model = whisper.load_model(model_size)
        print(f"[STT] Model loaded successfully.")

    # ─── Transcription ──────────────────────────────────────────────────

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe an audio file to text.

        Whisper natively handles .wav, .mp3, .ogg, .flac, .m4a
        (as long as ffmpeg is installed on the system).

        Args:
            audio_path: Path to the audio file.

        Returns:
            The raw transcript string.
        """
        print(f"[STT] Transcribing: {audio_path}")

        result = self.model.transcribe(
            audio_path,
            language="hi",          # Hindi — Whisper handles Hinglish under this code
            initial_prompt=self.DOMAIN_PROMPT,  # Anchor the decoder to our domain
            fp16=False,             # CPU-safe (no GPU float16 needed)
        )

        transcript = result["text"].strip()
        print(f"[STT] Transcript: {transcript}")
        return transcript

    # ─── End-to-End Pipeline ────────────────────────────────────────────

    def process_audio(self, audio_path: str) -> dict:
        """
        Full pipeline: Audio File → Transcript

        This method generates the raw transcript which will later be fed
        into the NLP layer for intent classification and slot filling.

        Args:
            audio_path: Path to the audio file (.ogg, .wav, .mp3, etc.)

        Returns:
            {
                "transcript": str            # The raw Whisper output
            }
        """
        transcript = self.transcribe(audio_path)

        return {
            "transcript": transcript
        }


# ═══════════════════════════════════════════════════════════════════════
# Test Runner
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import json
    import sys

    # Default test file — pass a custom path as CLI argument
    AUDIO = sys.argv[1] if len(sys.argv) > 1 else "../../audio_test.ogg"

    # Upgraded from 'base' to 'small' for significantly better Hinglish accuracy
    stt = VoiceTranscriber(model_size="small")
    result = stt.process_audio(AUDIO)

    print("\n========== FINAL OUTPUT ==========")
    print(json.dumps(result, indent=4))

