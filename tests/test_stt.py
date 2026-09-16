import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_faster_whisper_mock():
    from beau.voice.stt.provider import FasterWhisperSTT
    with patch("beau.voice.stt.provider.WhisperModel") as mock_w:
        mock_w.return_value.transcribe.return_value = ([type("S", (), {"text": "hello"})()], None)
        s = FasterWhisperSTT()
        out = await s.transcribe(b"fake_wav")
        assert "hello" in out

def test_get_stt_factory():
    from beau.voice.stt.provider import get_stt
    s = get_stt(provider="faster_whisper")
    assert s is not None
