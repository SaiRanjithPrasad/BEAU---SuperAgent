import pytest


@pytest.mark.asyncio
async def test_edge_tts_live_or_skip():
    from beau.voice.tts_provider import EdgeTTSProvider
    p = EdgeTTSProvider()
    if not p.is_available():
        pytest.skip("edge-tts not installed")
    audio = await p.tts("Hello BEAU")
    assert len(audio) > 1000


def test_get_tts_auto_fallback():
    from beau.voice.tts_provider import get_tts
    import beau.core.config as cfg
    # with auto and fish key set, prefers fish (even if 402 at call time)
    provider = get_tts(prefer="edge")
    assert provider.__class__.__name__ == "EdgeTTSProvider"


@pytest.mark.asyncio
async def test_speak_falls_back_to_edge():
    from beau.voice.tts_provider import speak
    from unittest.mock import AsyncMock, patch
    # force fish to fail with 402, edge to succeed
    with patch("beau.voice.tts_provider.FishAudioClient") as mock_fish:
        inst = mock_fish.return_value
        inst.is_available.return_value = True
        inst.tts = AsyncMock(side_effect=Exception("402 Payment Required"))
        with patch("beau.voice.tts_provider.EdgeTTSProvider") as mock_edge:
            einst = mock_edge.return_value
            einst.tts = AsyncMock(return_value=b"fake_mp3")
            audio, provider = await speak("hi")
            assert audio == b"fake_mp3"
            assert provider == "edge_tts"
