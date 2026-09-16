from unittest.mock import patch, AsyncMock

def test_fish_audio_client_cloud_mock():
    with patch("beau.voice.fish_audio.client.FishAudioSDK") as mock_sdk:
        mock_sdk.return_value.tts.return_value = b"fake_wav"
        from beau.voice.fish_audio.client import FishAudioClient
        c = FishAudioClient(api_key="fake", use_local=False)
        assert c.is_available() is True

def test_fish_audio_fallback_when_no_key():
    from beau.voice.fish_audio.client import FishAudioClient
    c = FishAudioClient(api_key="", use_local=False)
    assert c.is_available() is False
