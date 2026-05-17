import os
import tempfile
import whisper

_model = None

def load_model(model_name: str = "base") -> None:
    global _model
    _model = whisper.load_model(model_name)

def transcribe(audio_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        result = _model.transcribe(tmp_path)
        return result["text"].strip()
    finally:
        os.unlink(tmp_path)
