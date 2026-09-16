import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_beau_agent_has_jarvis_prompt():
    from beau.core.prompts import JARVIS_PROMPT
    assert "Jarvis" in JARVIS_PROMPT or "BEAU" in JARVIS_PROMPT
    assert len(JARVIS_PROMPT) > 50

@pytest.mark.asyncio
async def test_run_beau_mocked():
    with patch("beau.core.orchestrator.Runner.run", new_callable=AsyncMock) as mock_run:
        mock_run.return_value.final_output = "Hello, I am BEAU."
        from beau.core.orchestrator import run_beau
        out = await run_beau("hi")
        assert "BEAU" in out
        mock_run.assert_awaited_once()
