# tests/test_api.py
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

def test_chat_endpoint():
    with patch("beau.api.server.run_beau", new_callable=AsyncMock) as mock:
        mock.return_value = "Hello BEAU"
        from beau.api.server import app
        client = TestClient(app)
        r = client.post("/v1/chat", json={"message": "hi"})
        assert r.status_code == 200
        assert "BEAU" in r.json()["reply"]
