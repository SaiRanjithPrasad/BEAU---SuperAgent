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


@pytest.mark.asyncio
async def test_run_beau_fallback_on_failure():
    from beau.core.orchestrator import run_beau

    mock_run = AsyncMock()
    mock_run.side_effect = [
        Exception("404 model not found"),
        type("R", (), {"final_output": "fallback response"})(),
    ]
    with patch("beau.core.orchestrator.Runner.run", mock_run):
        out = await run_beau("hi")
    assert out == "fallback response"
    assert mock_run.call_count == 2
    assert mock_run.call_args_list[0].kwargs["run_config"].model == "meta/muse-spark-1.2-contributor"
    assert mock_run.call_args_list[1].kwargs["run_config"].model == "google/gemini-3.5-flash-lite"


@pytest.mark.asyncio
async def test_run_beau_all_models_fail():
    from beau.core.orchestrator import run_beau

    mock_run = AsyncMock(side_effect=Exception("model error"))
    with patch("beau.core.orchestrator.Runner.run", mock_run):
        with pytest.raises(RuntimeError, match="All OpenRouter models failed"):
            await run_beau("hi")
    assert mock_run.call_count == 2
