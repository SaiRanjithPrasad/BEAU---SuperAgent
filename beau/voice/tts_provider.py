"""Free TTS fallback — Edge TTS (Microsoft, no key) + Piper (offline).

Used automatically when Fish Audio returns 402/insufficient_balance or is
unconfigured. Mirrors the beau/voice/stt/provider.py abstraction pattern.
"""
import logging

from beau.core.config import EDGE_TTS_VOICE

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


def get_tts(prefer: str = "auto"):
    """Return the first available TTS provider.

    Order for "auto": FishAudioClient (if configured) -> EdgeTTSProvider.
    """
    from beau.core.config import TTS_PROVIDER, FISH_AUDIO_API_KEY

    want = (prefer or TTS_PROVIDER or "auto").lower()
    if want in ("edge",):
        return EdgeTTSProvider()
    if want in ("fish_audio", "fish", "fishaudio"):
        from beau.voice.fish_audio.client import FishAudioClient
        return FishAudioClient()
    # auto
    from beau.voice.fish_audio.client import FishAudioClient
    fish = FishAudioClient()
    if FISH_AUDIO_API_KEY and fish.is_available():
        return fish
    return EdgeTTSProvider()


async def speak(text: str, voice: str = None) -> tuple[bytes, str]:
    """Speak text with best available provider.

    Returns (audio_bytes, provider_name). Falls back from Fish Audio
    (402/insufficient_balance) to Edge TTS automatically.
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
    edge = EdgeTTSProvider(voice or EDGE_TTS_VOICE)
    return await edge.tts(text, voice), "edge_tts"
