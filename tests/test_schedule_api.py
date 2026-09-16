from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


def test_schedule_api():
    with patch("beau.tools.scheduler.schedule", return_value="job_abc123"):
        from beau.api.server import app
        client = TestClient(app)
        r = client.post("/v1/schedule", json={
            "kind": "research", "payload": "hello", "every_secs": 300,
        })
        assert r.status_code == 200
        assert r.json()["job_id"] == "job_abc123"


def test_unschedule_api():
    with patch("beau.tools.scheduler.unschedule", return_value=True):
        from beau.api.server import app
        client = TestClient(app)
        r = client.delete("/v1/schedule/job_abc123")
        assert r.status_code == 200
        assert r.json()["removed"] is True


def test_list_schedule_api():
    with patch("beau.tools.scheduler.list_jobs", return_value=[{"id": "job_abc123", "kind": "chat"}]):
        from beau.api.server import app
        client = TestClient(app)
        r = client.get("/v1/schedule")
        assert r.status_code == 200
        assert len(r.json()["jobs"]) == 1


def test_lifespan_starts_and_stops_scheduler():
    with patch("beau.api.server.start", return_value=2) as mock_start, \
         patch("beau.api.server.stop") as mock_stop:
        from beau.api.server import app, lifespan
        import asyncio
        async def run():
            async with lifespan(app):
                pass
        asyncio.run(run())
        mock_start.assert_called_once()
        mock_stop.assert_called_once()
