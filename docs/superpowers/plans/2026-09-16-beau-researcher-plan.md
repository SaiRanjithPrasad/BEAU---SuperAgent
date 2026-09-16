# BEAU Researcher Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `beau/tools/researcher.py` stub with cheap lean researcher (planner 3 → search knowledge-only ×3 → writer 1-2 pages) via direct port of `agents/2_openai/deep_research/*`, exposing both `function_tool` + `POST /v1/research`.

**Architecture:** Direct Port Approach 1 — copy `planner_agent.py:22`, `search_agent.py:14`, `writer_agent.py:24` pattern into `beau/tools/research/` with `HOW_MANY_SEARCHES=3` (vs 5) and `tools=[]` cheap; `beau/tools/researcher.py` orchestrates `Runner.run` gather; `beau/core/orchestrator.py` exposes `research_tool`, `beau/api/server.py` exposes `POST /v1/research`.

**Tech Stack:** Python 3.12+, `openai`, `openai-agents` (`agents` SDK `Agent/Runner`, `ModelSettings`), `pydantic`, `fastapi`, `pytest-asyncio`, `beau.core.config` (`OPENROUTER_MODEL=meta/muse-spark-1.2-contributor`)

**Spec:** `docs/superpowers/specs/2026-09-16-beau-researcher-design.md`

## Global Constraints

- OPENROUTER_MODEL=meta/muse-spark-1.2-contributor via `beau/core/config.py:1` mirrors to `OPENAI_API_KEY/BASE_URL` via `load_config()` — all Agents use this model
- Cheap lean B: HOW_MANY_SEARCHES=3 (not 5), writer 1-2 pages 300-500w (not 5-10 pages 1000+), search `tools=[]` on OpenRouter (no WebSearchTool, no Tavily cost) per `search_agent.py:21`
- Repo https://github.com/SaiRanjithPrasad/BEAU---SuperAgent branch `main` @ `2b7689d`, Python >=3.12, `uv`
- Expose both `function_tool` for `beau/core/orchestrator.py:7` and `POST /v1/research` for `beau/api/server.py:9`
- Cost budget ~1550 tokens (planner 50 + 3×300 + writer 600) on `muse-spark-1.2-contributor` gratis

---

## File Structure

**Create:**
- `beau/tools/research/__init__.py` — package marker
- `beau/tools/research/planner.py` — `WebSearchItem`, `WebSearchPlan`, `planner_agent`
- `beau/tools/research/search.py` — `search_agent` (tools=[] lean)
- `beau/tools/research/writer.py` — `ReportData`, `writer_agent` (1-2 pages)
- `tests/test_researcher.py` — mocked unit tests for `research(query)`

**Modify:**
- `beau/core/config.py:1` — add `HOW_MANY_SEARCHES = int(os.getenv("HOW_MANY_SEARCHES", 3))`
- `.env.example:1` — add `HOW_MANY_SEARCHES=3`
- `beau/tools/researcher.py:1` — replace stub with `async def research(query: str) -> str` orchestrator + `ResearchResult` handling
- `beau/core/orchestrator.py:1` — add `research_tool` function_tool wiring
- `beau/api/server.py:1` — add `POST /v1/research`

---

### Task 1: Config Lean Tuning

**Files:**
- Modify: `beau/core/config.py:1`, `.env.example:1`
- Test: `tests/test_config.py:1` (add one assertion)

**Interfaces:**
- Consumes: `os.getenv("HOW_MANY_SEARCHES")`
- Produces: `beau.core.config.HOW_MANY_SEARCHES: int = 3`

- [ ] **Step 1: Write failing test**

```python
# add to tests/test_config.py
def test_how_many_searches_default():
    import importlib, beau.core.config as cfg
    importlib.reload(cfg)
    assert cfg.HOW_MANY_SEARCHES == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py::test_how_many_searches_default -v`
Expected: FAIL `AttributeError: module 'beau.core.config' has no attribute 'HOW_MANY_SEARCHES'`

- [ ] **Step 3: Write minimal implementation**

```python
# beau/core/config.py — add after BEAU_API_PORT line
HOW_MANY_SEARCHES = int(os.getenv("HOW_MANY_SEARCHES", 3))
```

```env
# .env.example — add
HOW_MANY_SEARCHES=3
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py::test_how_many_searches_default -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add beau/core/config.py .env.example tests/test_config.py
git commit -m "feat: config HOW_MANY_SEARCHES=3 lean B"
```

---

### Task 2: Create Research Sub-Agents (Direct Port)

**Files:**
- Create: `beau/tools/research/__init__.py`, `beau/tools/research/planner.py`, `beau/tools/research/search.py`, `beau/tools/research/writer.py`
- Test: `tests/test_researcher_planner.py` (import smoke)

**Interfaces:**
- Consumes: `beau.core.config.OPENROUTER_MODEL`, `beau.core.config.HOW_MANY_SEARCHES`
- Produces: `beau.tools.research.planner.{WebSearchItem, WebSearchPlan, planner_agent}`, `beau.tools.research.search.search_agent`, `beau.tools.research.writer.{ReportData, writer_agent}`

- [ ] **Step 1: Write failing test**

```python
# tests/test_researcher_planner.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_researcher_planner.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'beau.tools.research.planner'`

- [ ] **Step 3: Write minimal implementation**

```python
# beau/tools/research/__init__.py
# empty

# beau/tools/research/planner.py
from pydantic import BaseModel, Field
from agents import Agent
from beau.core.config import OPENROUTER_MODEL, HOW_MANY_SEARCHES
INSTRUCTIONS = f"""
You are a research assistant. Given a user query, come up with a set of web searches
to perform to best answer the query. Output {HOW_MANY_SEARCHES} terms to query for.
"""
class WebSearchItem(BaseModel):
    reason: str = Field(description="Your reasoning for why this search is important to the query.")
    query: str = Field(description="The search term to use for the web search.")
class WebSearchPlan(BaseModel):
    searches: list[WebSearchItem] = Field(description="A list of web searches to perform to best answer the query.")
planner_agent = Agent(name="Planner Agent", instructions=INSTRUCTIONS, model=OPENROUTER_MODEL, output_type=WebSearchPlan)

# beau/tools/research/search.py
from agents import Agent, WebSearchTool, ModelSettings
import os
from beau.core.config import OPENROUTER_MODEL
INSTRUCTIONS = """
You are a research assistant. Given a search term, you search the web for that term and 
produce a concise summary of the results. The summary must 2-3 paragraphs and less than 300 words.
Capture the main points and be succinct. Reply only with the summary.
"""
if os.getenv("OPENROUTER_API_KEY"):
    tools = []
    settings = ModelSettings()
else:
    settings = ModelSettings(tool_choice="required")
    tools = [WebSearchTool()]
search_agent = Agent(name="Search Agent", instructions=INSTRUCTIONS, tools=tools, model=OPENROUTER_MODEL, model_settings=settings)

# beau/tools/research/writer.py
from pydantic import BaseModel, Field
from agents import Agent
from beau.core.config import OPENROUTER_MODEL
INSTRUCTIONS = """
You are a senior researcher tasked with writing a cohesive report for a research query.
You will be provided with the original query, and some research.
Generate a comprehensive report based on the research and the query.
The final output should be in markdown format, and it should be lengthy and detailed. Aim 
for 1-2 pages of content, 300-500 words (lean B, cheap).
"""
class ReportData(BaseModel):
    short_summary: str = Field(description="A short 2-3 sentence summary of the findings.")
    markdown_report: str = Field(description="The final report")
    follow_up_questions: list[str] = Field(description="Suggested topics to research further")
writer_agent = Agent(name="Writer Agent", instructions=INSTRUCTIONS, model=OPENROUTER_MODEL, output_type=ReportData)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_researcher_planner.py -v`
Expected: PASS 3/3

- [ ] **Step 5: Commit**

```bash
git add beau/tools/research/ tests/test_researcher_planner.py
git commit -m "feat: research sub-agents direct port (planner 3, search lean, writer 1-2 pages)"
```

---

### Task 3: Lean Researcher Orchestrator

**Files:**
- Modify: `beau/tools/researcher.py:1`
- Test: `tests/test_researcher.py`

**Interfaces:**
- Consumes: `beau.tools.research.planner.{planner_agent, WebSearchPlan}`, `beau.tools.research.search.search_agent`, `beau.tools.research.writer.{writer_agent, ReportData}`, `beau.memory.store.MemoryStore`, `agents.Runner`
- Produces: `async def research(query: str) -> str` returns `markdown_report`; `async def research_full(query: str) -> ReportData` optional

- [ ] **Step 1: Write failing test**

```python
# tests/test_researcher.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_researcher.py -v`
Expected: FAIL `AssertionError: "[Research stub` == ...` or `AttributeError`

- [ ] **Step 3: Write minimal implementation**

```python
# beau/tools/researcher.py
import asyncio
from agents import Runner
from beau.tools.research.planner import planner_agent, WebSearchPlan
from beau.tools.research.search import search_agent
from beau.tools.research.writer import writer_agent, ReportData

async def research(query: str) -> str:
    # 1. planner
    try:
        plan_result = await Runner.run(planner_agent, query)
        plan: WebSearchPlan = plan_result.final_output
        searches = plan.searches[:3] if plan and plan.searches else []
        if not searches:
            from beau.tools.research.planner import WebSearchItem
            searches = [WebSearchItem(reason="fallback", query=query)]
    except Exception:
        from beau.tools.research.planner import WebSearchItem
        searches = [WebSearchItem(reason="fallback", query=query)]

    # 2. search ×3 gather
    summaries = []
    for item in searches:
        try:
            r = await Runner.run(search_agent, item.query)
            summaries.append(r.final_output if isinstance(r.final_output, str) else str(r.final_output))
        except Exception as e:
            summaries.append(f"[Search error for {item.query}: {e}]")

    research_text = "\n\n".join(summaries)

    # 3. writer
    try:
        writer_input = f"Query: {query}\n\nResearch:\n{research_text}"
        w = await Runner.run(writer_agent, writer_input)
        report: ReportData = w.final_output
        markdown = report.markdown_report
    except Exception:
        markdown = research_text  # fallback

    # 4. memory best-effort
    try:
        from beau.memory.store import MemoryStore
        MemoryStore().save(query, markdown[:2000])
    except Exception:
        pass

    return markdown

# for tests that need full object
async def research_full(query: str) -> ReportData:
    md = await research(query)
    return ReportData(short_summary=md[:200], markdown_report=md, follow_up_questions=[])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_researcher.py -v`
Expected: PASS 3/3 (mocked)

- [ ] **Step 5: Commit**

```bash
git add beau/tools/researcher.py tests/test_researcher.py
git commit -m "feat: lean researcher orchestrator (planner 3→search×3→writer 1-2 pages, fallback)"
```

---

### Task 4: Orchestrator Tool + API Wiring

**Files:**
- Modify: `beau/core/orchestrator.py:1`, `beau/api/server.py:1`
- Test: `tests/test_researcher_api.py`

**Interfaces:**
- Consumes: `beau.tools.researcher.research(query) -> str`
- Produces: `beau.core.orchestrator.research_tool(query) -> str` as `function_tool` for BEAU Agent; `POST /v1/research` -> `{report, summary}`

- [ ] **Step 1: Write failing test**

```python
# tests/test_researcher_api.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_researcher_api.py -v`
Expected: FAIL `404` or `research not found`

- [ ] **Step 3: Write minimal implementation**

```python
# beau/core/orchestrator.py — add
from agents import Agent, Runner, function_tool
import asyncio
from beau.tools.researcher import research

@function_tool
def research_tool(query: str) -> str:
    """Research a query using lean planner→search→writer pipeline (cheap, knowledge-only)."""
    return asyncio.run(research(query))

def get_beau_agent():
    return Agent(name="BEAU", instructions=JARVIS_PROMPT, model=OPENROUTER_MODEL, tools=[research_tool])

# beau/api/server.py — add
from pydantic import BaseModel
from beau.tools.researcher import research
class ResearchReq(BaseModel):
    query: str
class ResearchResp(BaseModel):
    report: str
    summary: str
@app.post("/v1/research", response_model=ResearchResp)
async def research_endpoint(req: ResearchReq):
    report = await research(req.query)
    return ResearchResp(report=report, summary=report[:200])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_researcher_api.py -v`
Expected: PASS 2/2

- [ ] **Step 5: Commit**

```bash
git add beau/core/orchestrator.py beau/api/server.py tests/test_researcher_api.py
git commit -m "feat: wire researcher as BEAU tool + POST /v1/research"
```

---

## Self-Review

- **Spec coverage:** §2 G1→Task3 `research()`, §2 G2→Task4 `research_tool`, §2 G3→Task4 `POST /v1/research`, §2 G4→Task3 `MemoryStore.save`, §2 G5→Task1 `HOW_MANY_SEARCHES=3` lean; §3.1 Components→Task2 planner/search/writer; §3.3 Data flow→Task3 fallback handling; §5 Error handling→Task3 try/except branches; §6 Testing→Tasks 2-4 tests.
- **Placeholder scan:** No TODO/TBD — all steps have concrete code blocks.
- **Type consistency:** `WebSearchItem(reason: str, query: str)`, `WebSearchPlan(searches: list[WebSearchItem])`, `ReportData(short_summary, markdown_report, follow_up_questions: list[str])`, `research(query: str) -> str`, `research_tool(query: str) -> str`, `ResearchReq(query: str)`, `ResearchResp(report: str, summary: str)` consistent across tasks.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-16-beau-researcher-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - dispatch fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
