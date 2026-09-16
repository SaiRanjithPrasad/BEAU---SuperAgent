def test_planner_importable():
    from beau.tools.research.planner import planner_agent, HOW_MANY_SEARCHES
    assert HOW_MANY_SEARCHES == 3
    assert planner_agent.name == "Planner Agent"

def test_search_importable():
    from beau.tools.research.search import search_agent
    assert search_agent.name == "Search Agent"
    # cheap: no tools on OpenRouter when key set
    import os
    if os.getenv("OPENROUTER_API_KEY"):
        assert search_agent.tools == []

def test_writer_importable():
    from beau.tools.research.writer import writer_agent, ReportData
    assert writer_agent.name == "Writer Agent"
    assert "1-2 pages" in writer_agent.instructions or "300" in writer_agent.instructions
