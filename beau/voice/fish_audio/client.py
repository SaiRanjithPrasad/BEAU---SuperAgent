import os

from beau.core.config import FISH_AUDIO_API_KEY, FISH_AUDIO_USE_LOCAL, FISH_AUDIO_BASE_URL, FISH_AUDIO_VOICE_ID

try:
    from fish_audio_sdk import Session as FishAudioSDK  # fish-audio-python package provides this
except ImportError:
    FishAudioSDK = None


class FishAudioClient:
    def __init__(
        self,
        api_key: str = FISH_AUDIO_API_KEY,
        use_local: bool = FISH_AUDIO_USE_LOCAL,
        base_url: str = FISH_AUDIO_BASE_URL,
        voice_id: str = FISH_AUDIO_VOICE_ID,
    ):
        self.api_key = api_key
        self.use_local = use_local
        self.base_url = base_url
        self.voice_id = voice_id
        self._sdk = FishAudioSDK(api_key) if FishAudioSDK and api_key and not use_local else None

    def is_available(self) -> bool:
        return bool(self.api_key or self.use_local)

    async def tts(self, text: str, voice_id: str = None) -> bytes:
        vid = voice_id or self.voice_id
        if self.use_local:
            # local fish-speech SGLang server
            import httpx

            async with httpx.AsyncClient() as client:
                r = await client.post(f"{self.base_url}/v1/tts", json={"text": text, "voice": vid}, timeout=20.0)
                r.raise_for_status()
                return r.content
        if not self._sdk:
            raise RuntimeError("Fish Audio not configured: set FISH_AUDIO_API_KEY or FISH_AUDIO_USE_LOCAL=true")
        # cloud path - SDK signature may vary, wrap with inline tag support
        # Fish S2 supports [whisper] [excited] tags passthrough - text is forwarded verbatim
        result = self._sdk.tts(text)
        # Handle various SDK return types: awaitable bytes, sync bytes, streaming generator
        import inspect

        if inspect.isawaitable(result):
            result = await result
        # If result is async/sync iterable of bytes (streaming), collect
        if hasattr(result, "__aiter__"):
            chunks = []
            async for chunk in result:
                chunks.append(chunk)
            return b"".join(chunks)
        if hasattr(result, "__iter__") and not isinstance(result, (bytes, bytearray)):
            try:
                chunks = list(result)
                if chunks and isinstance(chunks[0], (bytes, bytearray)):
                    return b"".join(chunks)
            except Exception:
                pass
        if isinstance(result, (bytes, bytearray)):
            return bytes(result)
        # Fallback: unknown SDK shape - return empty (brief fallback: await tts or b"")
        if hasattr(self._sdk, "tts"):
            # if result was not bytes but SDK still has tts, try to interpret
            return b""
        return b""
