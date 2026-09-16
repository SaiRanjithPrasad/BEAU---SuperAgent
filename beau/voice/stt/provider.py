from abc import ABC, abstractmethod
from beau.core.config import STT_PROVIDER

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

class STTProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes) -> str: ...

class FasterWhisperSTT(STTProvider):
    async def transcribe(self, audio_bytes: bytes) -> str:
        try:
            # Prefer module-level WhisperModel (patched in tests as beau.voice.stt.provider.WhisperModel)
            # Fallback to direct import if module-level is None (ImportError case)
            _WhisperModel = WhisperModel
            if _WhisperModel is None:
                from faster_whisper import WhisperModel as _WhisperModel
            import tempfile, os
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes); path = f.name
            model = _WhisperModel("base", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(path)
            os.unlink(path)
            return " ".join(s.text for s in segments)
        except Exception as e:
            return f"[STT error: {e}]"

class OpenCodeVoiceSTT(STTProvider):
    async def transcribe(self, audio_bytes: bytes) -> str:
        # SPIKE: check if `opencode` CLI exposes voice-input; placeholder delegates to FasterWhisper until verified
        # TODO after spike: if opencode voice-input exists, call it via subprocess/HTTP
        fallback = FasterWhisperSTT()
        return await fallback.transcribe(audio_bytes)

def get_stt(provider: str = STT_PROVIDER) -> STTProvider:
    if provider == "opencode_voice":
        return OpenCodeVoiceSTT()
    return FasterWhisperSTT()
