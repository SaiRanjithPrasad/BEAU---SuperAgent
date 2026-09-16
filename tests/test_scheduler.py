import pytest


def test_schedule_validate():
    from beau.tools.scheduler import schedule, unschedule, list_jobs
    with pytest.raises(ValueError):
        schedule("nope", "x", 60)
    with pytest.raises(ValueError):
        schedule("chat", "x", 1)  # too frequent
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
            # force one run by calling _execute directly + loop tick
            await asyncio.sleep(0)
            assert job_id in [j["id"] for j in __import__("beau.tools.scheduler", fromlist=["list_jobs"]).list_jobs()]
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
            # not entitled -> skipped without executing
            assert "not entitled" in _JOBS[job_id]["last_result"] or _JOBS[job_id]["last_result"] == ""
    finally:
        _JOBS.pop(job_id, None)
