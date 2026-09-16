from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

def test_act_api():
    with patch("beau.api.server.act", new_callable=AsyncMock) as mock_act:
        mock_act.return_value = "acted"
        from beau.api.server import app
        client = TestClient(app)
        r = client.post("/v1/act", json={"task": "hello"})
        assert r.status_code == 200
        assert "acted" in r.json()["result"]

def test_orchestrator_has_act_tool():
    from beau.core.orchestrator import get_beau_agent
    agent = get_beau_agent()
    tool_names = [t.name if hasattr(t, 'name') else str(t) for t in getattr(agent, 'tools', [])]
    assert any("act" in n.lower() for n in tool_names)
