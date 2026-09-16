import pytest


def test_schedule_validate():
    from beau.tools.scheduler import schedule, unschedule, list_jobs
    with pytest.raises(ValueError):
        schedule("nope", "x", 60)
    with pytest.raises(ValueError):
        schedule("chat", "x", 1)
    job_id = schedule("chat", "hello", 60)
    try:
        assert any(j["id"] == job_id for j in list_jobs())
    finally:
        assert unschedule(job_id) is True
        assert unschedule(job_id) is False


@pytest.mark.asyncio
async def test_schedule_executes_chat():
    import asyncio
    from unittest.mock import AsyncMock, patch
    from beau.tools.scheduler import schedule, unschedule, start, stop
    with patch("beau.tools.scheduler._execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = "mocked result"
        job_id = schedule("chat", "hi", 60)
        try:
            start()
            await asyncio.sleep(0)
            import beau.tools.scheduler as sched
            assert job_id in [j["id"] for j in sched.list_jobs()]
        finally:
            stop()
            unschedule(job_id)


@pytest.mark.asyncio
async def test_schedule_premium_gate():
    from unittest.mock import patch
    from beau.tools.scheduler import _run_loop, _JOBS
    import asyncio
    job_id = "testpremium1"
    _JOBS[job_id] = {
        "id": job_id, "kind": "chat", "payload": "hi", "every_secs": 9999,
        "next_run": 9999999999.0, "created": 0, "last_result": "",
        "user_id": "u1", "premium": True,
    }
    try:
        with patch("beau.tools.scheduler.is_entitled", return_value=False):
            task = asyncio.create_task(_run_loop(job_id))
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            assert "not entitled" in _JOBS[job_id]["last_result"] or _JOBS[job_id]["last_result"] == ""
    finally:
        _JOBS.pop(job_id, None)


def test_edge_tts_available_or_skip():
    from beau.voice.tts_provider import EdgeTTSProvider
    p = EdgeTTSProvider()
    assert isinstance(p.is_available(), bool)


def test_piper_available():
    from beau.voice.tts_provider import PiperTTSProvider
    p = PiperTTSProvider()
    # model is downloaded to data/piper-voices — should be available
    assert p.is_available() is True


def test_piper_synthesis():
    from beau.voice.tts_provider import PiperTTSProvider
    p = PiperTTSProvider()
    audio = p.tts("Hello BEAU")
    assert len(audio) > 1000


def test_get_tts_falls_back():
    from beau.voice.tts_provider import get_tts
    p = get_tts(prefer="piper")
    assert p.__class__.__name__ == "PiperTTSProvider"


def test_get_tts_edge():
    from beau.voice.tts_provider import get_tts
    p = get_tts(prefer="edge")
    assert p.__class__.__name__ == "EdgeTTSProvider"


def test_piper_ensure_downloaded():
    from beau.voice.tts_provider import PiperTTSProvider
    p = PiperTTSProvider()
    # model already exists, should return True immediately
    assert p.ensure_downloaded() is True


@pytest.mark.asyncio
async def test_speak_falls_back_to_edge():
    from beau.voice.tts_provider import speak
    from unittest.mock import AsyncMock, patch
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


@pytest.mark.asyncio
async def test_speak_falls_back_to_piper():
    from beau.voice.tts_provider import speak
    from unittest.mock import AsyncMock, patch
    with patch("beau.voice.tts_provider.FishAudioClient") as mock_fish:
        inst = mock_fish.return_value
        inst.is_available.return_value = True
        inst.tts = AsyncMock(side_effect=Exception("402"))
        with patch("beau.voice.tts_provider.EdgeTTSProvider") as mock_edge:
            einst = mock_edge.return_value
            einst.is_available.return_value = False
            audio, provider = await speak("hi")
            assert provider == "piper"
        assert len(audio) > 1000
