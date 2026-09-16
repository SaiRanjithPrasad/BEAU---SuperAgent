# tests/test_actor_tools.py
import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_get_all_tools():
    from beau.tools.actor.tools import get_all_tools
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tools, sessions = await get_all_tools(tmp)
        names = [t.name if hasattr(t, 'name') else str(t) for t in tools]
        assert any("write" in n.lower() for n in names)
        assert any("read" in n.lower() for n in names)

@pytest.mark.asyncio
async def test_run_bash_needs_confirm():
    from beau.tools.actor.tools import get_all_tools
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmp:
        tools, _ = await get_all_tools(tmp)
        bash_tool = next(t for t in tools if "bash" in t.name.lower())
        # destructive command should return needs_confirm
        result = await bash_tool.ainvoke({"command": "rm -rf /tmp/evil"}) if hasattr(bash_tool, 'ainvoke') else bash_tool.invoke({"command": "rm -rf /tmp/evil"})
        assert "needs_confirm" in str(result).lower() or "confirm" in str(result).lower()
