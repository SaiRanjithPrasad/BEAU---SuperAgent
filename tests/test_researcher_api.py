from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

def test_research_api():
    with patch("beau.api.server.research", new_callable=AsyncMock) as mock_res:
        mock_res.return_value = "# Mock Report"
        from beau.api.server import app
        client = TestClient(app)
        r = client.post("/v1/research", json={"query": "hello"})
        assert r.status_code == 200
        assert "Mock Report" in r.json()["report"]

def test_orchestrator_has_research_tool():
    from beau.core.orchestrator import get_beau_agent
    agent = get_beau_agent()
    # agent tools should include research_tool when mocked
    tool_names = [t.name if hasattr(t, 'name') else str(t) for t in getattr(agent, 'tools', [])]
    assert any("research" in n.lower() for n in tool_names)
