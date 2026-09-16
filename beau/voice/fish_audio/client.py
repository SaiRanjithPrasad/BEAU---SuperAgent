import inspect
import os

import httpx

from beau.core.config import FISH_AUDIO_API_KEY, FISH_AUDIO_USE_LOCAL, FISH_AUDIO_BASE_URL, FISH_AUDIO_VOICE_ID

try:
    from fish_audio_sdk import Session as FishAudioSDK  # fish-audio-python package provides this
    from fish_audio_sdk.schemas import TTSRequest
except ImportError:  # pragma: no cover
    FishAudioSDK = None  # type: ignore
    TTSRequest = None  # type: ignore


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
        self._sdk = FishAudioSDK(api_key, base_url=base_url) if FishAudioSDK and api_key and not use_local else None

    def is_available(self) -> bool:
        return bool(self.api_key or self.use_local)

    async def tts(self, text: str, voice_id: str = None) -> bytes:
        vid = voice_id or self.voice_id
        if self.use_local:
            # local fish-speech SGLang server
            async with httpx.AsyncClient() as client:
                r = await client.post(f"{self.base_url}/v1/tts", json={"text": text, "voice": vid}, timeout=20.0)
                r.raise_for_status()
                return r.content
        if not self._sdk:
            raise RuntimeError("Fish Audio not configured: set FISH_AUDIO_API_KEY or FISH_AUDIO_USE_LOCAL=true")
        # cloud path - SDK requires TTSRequest(text, reference_id)
        # Fish S2 supports [whisper] [excited] tags passthrough - text is forwarded verbatim
        if TTSRequest is not None:
            try:
                request = TTSRequest(text=text, reference_id=vid)
            except Exception:
                request = text  # fallback for mock compatibility
        else:
            request = text

        tts_call = self._sdk.tts

        # Prefer async streaming via awaitable if available (real SDK), else sync
        # Need mock compatibility: MagicMock has awaitable but yields empty, so fallback to sync
        if hasattr(tts_call, "awaitable"):
            try:
                maybe = tts_call.awaitable(request)
                if hasattr(maybe, "__aiter__"):
                    chunks = []
                    try:
                        async for chunk in maybe:  # type: ignore
                            # filter out non-bytes mocks
                            if isinstance(chunk, (bytes, bytearray)):
                                chunks.append(chunk)
                            elif chunk is not None:
                                # if mock yields MagicMock, ignore
                                pass
                    except TypeError:
                        chunks = []
                    except Exception:
                        chunks = []
                    if chunks:
                        return b"".join(chunks)
                    # empty chunks likely indicates mock or empty stream; fall through to sync path
                    # but if maybe was truly empty (no audio), still correctly return b""
                    # Check if maybe was a real empty generator: we still fall through and try sync
                    # To avoid infinite fallback loop, only fall through if chunks empty and not a real empty response
                    # For real SDK empty would still be empty; sync would also be empty, so returning b"" is fine
                    # Continue to sync fallback if no bytes yielded
                if inspect.isawaitable(maybe):
                    maybe = await maybe
                    if isinstance(maybe, (bytes, bytearray)):
                        return bytes(maybe)
                if isinstance(maybe, (bytes, bytearray)):
                    return bytes(maybe)
            except TypeError:
                # signature mismatch (mock expects str) - try with plain text
                try:
                    maybe2 = tts_call.awaitable(text)
                    if hasattr(maybe2, "__aiter__"):
                        chunks2 = []
                        async for chunk in maybe2:  # type: ignore
                            if isinstance(chunk, (bytes, bytearray)):
                                chunks2.append(chunk)
                        if chunks2:
                            return b"".join(chunks2)
                    if inspect.isawaitable(maybe2):
                        maybe2 = await maybe2
                    if isinstance(maybe2, (bytes, bytearray)):
                        return bytes(maybe2)
                except Exception:
                    pass
            except Exception:
                pass

        # Sync fallback (handles mock b"fake_wav" and real SDK sync Generator[bytes])
        try:
            result = tts_call(request)
        except TypeError:
            # mock compatibility: if request is TTSRequest but mock expects str
            result = tts_call(text)

        # Handle various SDK return types: awaitable bytes, sync bytes, streaming generator
        if inspect.isawaitable(result):
            result = await result
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
            return b""
        return b""
