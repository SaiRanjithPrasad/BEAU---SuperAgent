import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_act_simple():
    with patch("beau.tools.actor.sidekick.get_all_tools", new_callable=AsyncMock) as mock_tools:
        mock_tools.return_value = ([], [])
        with patch("beau.tools.actor.sidekick.ChatOpenAI") as mock_llm:
            mock_llm.return_value.with_structured_output.return_value = mock_llm.return_value
            with patch("beau.tools.actor.sidekick.create_agent") as mock_create:
                mock_create.return_value = AsyncMock(invoke=AsyncMock(return_value="done"))
                from beau.tools.actor import act
                out = await act("create file hello.txt")
                assert "done" in out or "hello" in out.lower()

@pytest.mark.asyncio
async def test_act_needs_confirm():
    # test that rm -rf triggers needs_confirm via tools
    from beau.tools.actor.tools import run_bash
    result = run_bash.invoke({"command": "rm -rf /tmp/test"})
    assert "needs_confirm" in result or "confirm" in result.lower()
