"""Free TTS fallback — Edge TTS (Microsoft, no key) + Piper (offline).

Used automatically when Fish Audio returns 402/insufficient_balance or is
unconfigured. Mirrors the beau/voice/stt/provider.py abstraction pattern.
"""
import logging
import os
import subprocess

from beau.core.config import EDGE_TTS_VOICE, PIPER_VOICE, PIPER_VOICE_DIR

logger = logging.getLogger(__name__)

try:
    import edge_tts
except ImportError:  # pragma: no cover
    edge_tts = None

try:
    from beau.voice.fish_audio.client import FishAudioClient
except ImportError:  # pragma: no cover
    FishAudioClient = None


class EdgeTTSProvider:
    """Free Microsoft Edge TTS — 400+ voices, no API key."""

    def __init__(self, voice: str = EDGE_TTS_VOICE):
        self.voice = voice

    def is_available(self) -> bool:
        return edge_tts is not None

    async def tts(self, text: str, voice: str = None) -> bytes:
        if edge_tts is None:
            raise RuntimeError("edge-tts not installed: uv add edge-tts")
        communicate = edge_tts.Communicate(text, voice or self.voice)
        chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
        if not chunks:
            raise RuntimeError("Edge TTS returned no audio")
        return b"".join(chunks)


class PiperTTSProvider:
    """Offline TTS via piper-tts (no key, no network after voice download)."""

    def __init__(self, voice: str = PIPER_VOICE, voice_dir: str = None):
        self.voice = voice
        self.voice_dir = voice_dir or PIPER_VOICE_DIR
        self._model_path = os.path.join(self.voice_dir, f"{voice}.onnx")
        self._config_path = os.path.join(self.voice_dir, f"{voice}.onnx.json")

    def is_available(self) -> bool:
        """Check piper binary + voice model exist."""
        if not self._model_exists():
            return False
        return True

    def _model_exists(self) -> bool:
        return os.path.isfile(self._model_path) and os.path.isfile(self._config_path)

    def ensure_downloaded(self) -> bool:
        """Download voice if missing. Returns True when ready."""
        if self._model_exists():
            return True
        try:
            os.makedirs(self.voice_dir, exist_ok=True)
            subprocess.run(
                [
                    "uv", "run", "python", "-m",
                    "piper.download_voices",
                    "--download-dir", self.voice_dir,
                    self.voice,
                ],
                check=True, capture_output=True, timeout=180,
            )
            return self._model_exists()
        except Exception as e:
            logger.warning("Piper voice download failed: %s", e)
            return False

    def tts(self, text: str, voice: str = None) -> bytes:
        """Synthesize text → WAV bytes using piper CLI."""
        model = self._model_path if voice is None or voice == self.voice else os.path.join(self.voice_dir, f"{voice}.onnx")
        config = self._config_path if voice is None or voice == self.voice else os.path.join(self.voice_dir, f"{voice}.onnx.json")
        if not os.path.isfile(model) or not os.path.isfile(config):
            if not self.ensure_downloaded():
                raise RuntimeError(f"Piper voice not available at {model}")
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as in_file:
            in_file.write(text.encode("utf-8"))
            in_path = in_file.name
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out_file:
            out_path = out_file.name
        try:
            result = subprocess.run(
                [
                    "uv", "run", "piper",
                    "-m", model,
                    "-c", config,
                    "-i", in_path,
                    "-f", out_path,
                ],
                capture_output=True, timeout=30,
            )
            if result.returncode != 0:
                raise RuntimeError(f"piper failed: {result.stderr.decode()[:500]}")
            with open(out_path, "rb") as f:
                return f.read()
        finally:
            for path in (in_path, out_path):
                try:
                    os.unlink(path)
                except OSError:
                    pass


def get_tts(prefer: str = "auto"):
    """Return the first available TTS provider.

    Order for "auto": FishAudioClient (if configured) -> EdgeTTSProvider -> PiperTTSProvider.
    """
    from beau.core.config import TTS_PROVIDER, FISH_AUDIO_API_KEY

    want = (prefer or TTS_PROVIDER or "auto").lower()
    if want in ("edge",):
        return EdgeTTSProvider()
    if want in ("fish_audio", "fish", "fishaudio"):
        from beau.voice.fish_audio.client import FishAudioClient
        return FishAudioClient()
    if want in ("piper",):
        return PiperTTSProvider()
    # auto
    from beau.voice.fish_audio.client import FishAudioClient
    fish = FishAudioClient()
    if FISH_AUDIO_API_KEY and fish.is_available():
        return fish
    return EdgeTTSProvider()


async def speak(text: str, voice: str = None) -> tuple[bytes, str]:
    """Speak text with best available provider.

    Returns (audio_bytes, provider_name). Falls back from Fish Audio
    (402/insufficient_balance) to Edge TTS to Piper automatically.
    """
    if FishAudioClient is not None:
        fish = FishAudioClient()
        if fish.is_available():
            try:
                audio = await fish.tts(text, voice_id=voice)
                if audio:
                    return audio, "fish_audio"
                logger.warning("Fish Audio returned empty audio, falling back to Edge TTS")
            except Exception as e:
                logger.warning("Fish Audio failed (%s), falling back to Edge TTS", e)
    if EdgeTTSProvider().is_available():
        try:
            edge = EdgeTTSProvider(voice or EDGE_TTS_VOICE)
            return await edge.tts(text, voice), "edge_tts"
        except Exception as e:
            logger.warning("Edge TTS failed (%s), falling back to Piper", e)
    if PiperTTSProvider().is_available() or PiperTTSProvider().ensure_downloaded():
        try:
            piper = PiperTTSProvider(PIPER_VOICE, PIPER_VOICE_DIR)
            return piper.tts(text, voice), "piper"
        except Exception as e:
            logger.warning("Piper TTS failed (%s)", e)
    raise RuntimeError("no TTS provider available")
