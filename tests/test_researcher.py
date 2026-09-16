import pytest
from unittest.mock import AsyncMock, patch
from pydantic import BaseModel

@pytest.mark.asyncio
async def test_research_lean_orchestrator():
    from beau.tools.research.planner import WebSearchPlan, WebSearchItem
    from beau.tools.research.writer import ReportData
    fake_plan = WebSearchPlan(searches=[
        WebSearchItem(reason="r1", query="q1"),
        WebSearchItem(reason="r2", query="q2"),
        WebSearchItem(reason="r3", query="q3"),
    ])
    fake_report = ReportData(short_summary="sum", markdown_report="# Report\nhello", follow_up_questions=["q?"])
    with patch("beau.tools.researcher.Runner.run", new_callable=AsyncMock) as mock_run:
        # sequence: planner -> search q1 -> search q2 -> search q3 -> writer
        mock_run.side_effect = [
            type("R", (), {"final_output": fake_plan})(),
            type("R", (), {"final_output": "summary1"})(),
            type("R", (), {"final_output": "summary2"})(),
            type("R", (), {"final_output": "summary3"})(),
            type("R", (), {"final_output": fake_report})(),
        ]
        from beau.tools.researcher import research
        out = await research("test query")
        assert "# Report" in out
        assert mock_run.call_count == 5

@pytest.mark.asyncio
async def test_research_fallback_empty_plan():
    from beau.tools.research.writer import ReportData
    from beau.tools.research.planner import WebSearchPlan
    empty_plan = WebSearchPlan(searches=[])
    fake_report = ReportData(short_summary="s", markdown_report="fallback", follow_up_questions=[])
    with patch("beau.tools.researcher.Runner.run", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = [
            type("R", (), {"final_output": empty_plan})(),
            type("R", (), {"final_output": "fallback summary"})(),
            type("R", (), {"final_output": fake_report})(),
        ]
        from beau.tools.researcher import research
        out = await research("empty")
        assert "fallback" in out

@pytest.mark.asyncio
async def test_research_writer_fallback():
    from beau.tools.research.planner import WebSearchPlan, WebSearchItem
    fake_plan = WebSearchPlan(searches=[WebSearchItem(reason="r", query="q1")])
    with patch("beau.tools.researcher.Runner.run", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = [
            type("R", (), {"final_output": fake_plan})(),
            type("R", (), {"final_output": "s1"})(),
            Exception("writer boom"),
        ]
        from beau.tools.researcher import research
        out = await research("boom")
        assert "s1" in out  # concatenated fallback
