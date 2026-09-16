# BEAU Researcher Phase 2 — Design Spec (Approach 1 Direct Port, Cheap Lean B)

**Date:** 2026-09-16  
**Repo:** https://github.com/SaiRanjithPrasad/BEAU---SuperAgent @ `c73bd7e`  
**Status:** Draft → Awaiting review before `writing-plans`  
**Parent spec:** `docs/superpowers/specs/2026-09-16-beau-superagent-design.md` §3.2 Researcher, Phase 2  
**Related plan:** `docs/superpowers/plans/2026-09-16-beau-superagent-plan.md` Task 8 stubs → replaced here  
**Approach:** **1 Direct Port (Fastest)** — copy `agents/2_openai/deep_research/*` verbatim with lean tweaks `HOW_MANY_SEARCHES=3`, 1-2 page writer, knowledge-only `tools=[]`, cheap  
**Priority:** `B Researches` lean per brainstorming 2026-09-16 (cheap > live search)

---

## 1. Summary

Replace `beau/tools/researcher.py:1` stub (`"[Research stub ...] — Phase 2"`) with lean researcher that reuses exactly `agents/2_openai/deep_research/planner_agent.py:17`, `search_agent.py:14`, `writer_agent.py:15` pattern, centralized on `beau/core/config.py:1` (`OPENROUTER_MODEL=meta/muse-spark-1.2-contributor`, `OPENAI_*` mirroring). Cheap by design: `HOW_MANY_SEARCHES=3` (`planner_agent.py:14` was 5), writer 1-2 pages not 5-10 (`writer_agent.py:19`), search `tools=[]` on OpenRouter (`search_agent.py:21`), no Tavily cost. Exposes both `function_tool` for `beau/core/orchestrator.py:7` BEAU handoff and `POST /v1/research` in `beau/api/server.py:9`.

---

## 2. Goals / Non-Goals

**Goals:**
- G1: `research(query: str) -> str` returns markdown report (lean 300-500w) + `ReportData.follow_up_questions` via `writer_agent.py:24`, using 3 cheap knowledge searches.
- G2: Expose as `function_tool` so BEAU `Agent(name="BEAU")` auto-routes "research X" without explicit API call.
- G3: Expose `POST /v1/research {query}` for explicit demo/client.
- G4: Persist to `beau/memory/store.py:1` `MemoryStore.save(query, markdown)` for A memory continuity.
- G5: Keep cost <1600 tokens total (planner 50 + 3×300 + writer 600) on `muse-spark-1.2-contributor` gratis.

**Non-Goals:**
- No Tavily/WebSearchTool live search (cheap), no email sending unless `USE_EMAIL=true` (`email_agent.py:14`), no FTS/vector recall upgrade, no orchestration refactoring beyond `researcher.py`.

**Success criteria:**
- `uv run pytest tests/test_researcher.py -v` mocked 3/3 passes (planner/search/writer), no live LLM.
- `uv run python -m beau.tools.researcher "test query"` live smoke returns markdown containing `follow_up_questions` when `OPENROUTER_API_KEY` set.
- `curl -X POST http://localhost:8000/v1/research -d '{"query":"hello"}'` → `{"report": "...", "summary": "..."}`.
- `BEAU` chat "research AI trends" triggers tool and returns markdown.

---

## 3. Architecture

### 3.1 Components

| Component | Path | Source | Responsibility |
|-----------|------|--------|----------------|
| **Planner** | `beau/tools/research/planner.py` | Copy `agents/2_openai/deep_research/planner_agent.py:22` | `WebSearchItem(reason, query)`, `WebSearchPlan(searches: list[WebSearchItem])`, `Agent(name="Planner Agent", model=OPENROUTER_MODEL, output_type=WebSearchPlan)` with `HOW_MANY_SEARCHES=3` env, `INSTRUCTIONS` f-string same as source |
| **Search** | `beau/tools/research/search.py` | Copy `search_agent.py:14` | `Agent(name="Search Agent", model=OPENROUTER_MODEL)` with `tools=[]` and `settings=ModelSettings()` on OpenRouter (cheap knowledge), `settings=ModelSettings(tool_choice="required") + [WebSearchTool()]` only if `OPENROUTER_API_KEY` not set — same branching as source `search_agent.py:21` |
| **Writer** | `beau/tools/research/writer.py` | Copy `writer_agent.py:15` | `ReportData(short_summary, markdown_report, follow_up_questions)`, `Agent(name="Writer Agent", model=OPENROUTER_MODEL, output_type=ReportData)` with `INSTRUCTIONS` tweaked to `1-2 pages, 300-500 words` (source was 5-10 pages, 1000+ words) |
| **Orchestrator** | `beau/tools/researcher.py:1` | Replaces stub | `async def research(query: str) -> str` → `Runner.run(planner, query)` → `gather(Runner.run(search, s.query) for s in plan.searches[:3])` → `Runner.run(writer, {"query": query, "research": summaries})` → `report.markdown_report`; saves to `MemoryStore` |
| **Tool** | `beau/core/orchestrator.py:7` | Modify | Add `@function_tool def research_tool(query: str) -> str: return asyncio.run(research(query))` and include in `get_beau_agent() tools=[research_tool]` |
| **API** | `beau/api/server.py:9` | Modify | Add `class ResearchReq(BaseModel): query: str` `class ResearchResp(BaseModel): report: str; summary: str; follow_ups: list[str]` `POST /v1/research` calling `research()` |

### 3.2 Files

**Create:**
- `beau/tools/research/__init__.py`
- `beau/tools/research/planner.py`
- `beau/tools/research/search.py`
- `beau/tools/research/writer.py`
- `tests/test_researcher.py`

**Modify:**
- `beau/tools/researcher.py:1` (replace stub with orchestrator above)
- `beau/core/orchestrator.py:1` (add `research_tool`)
- `beau/api/server.py:1` (add `POST /v1/research`)
- `beau/core/config.py:1` (add `HOW_MANY_SEARCHES = int(os.getenv("HOW_MANY_SEARCHES", 3))`)

### 3.3 Data Flow

```
User "research X" ─┬─ via BEAU chat → research_tool(query) ─┐
                   └─ via POST /v1/research {query} ────────┤
                                                           ▼
                                                    research(query: str)
                                                           │
                                              ┌─────────────┼─────────────┐
                                              ▼             │             ▼
                                       Planner Agent    (env HOW_MANY=3)  │
                                    Runner.run(planner, query)            │
                                              │                           │
                                              ▼                           │
                                    WebSearchPlan(searches: 3)            │
                                              │                           │
                          ┌───────────────────┼───────────────────┐       │
                          ▼                   ▼                   ▼       │
                    Search Agent 1      Search Agent 2      Search Agent 3│
                 Runner.run(search, s.query) each → summaries (<300w)     │
                          └───────────────────┼───────────────────┘       │
                                              ▼                           │
                                       Writer Agent                        │
                                    Runner.run(writer, {query, research}) │
                                              │                           │
                                              ▼                           │
                                    ReportData(markdown_report,            │
                                              short_summary,               │
                                              follow_up_questions)         │
                                              │                           │
                                              ▼                           │
                                    MemoryStore.save(query, markdown)     │
                                              │                           │
                                              ▼                           │
                                    return markdown_report                │
```

Spec §4.2 cheap: planner 50 tokens + 3×search 300 + writer 600 = ~1550.

---

## 4. Configuration

Add to `beau/core/config.py:1`:

```python
HOW_MANY_SEARCHES = int(os.getenv("HOW_MANY_SEARCHES", 3))  # lean B vs source 5
```

Reuse existing `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`, `BEAU_MEMORY_PATH`, `USE_EMAIL` (optional for `email_agent.py:14` — default `false` for lean).

`.env.example` add:

```
HOW_MANY_SEARCHES=3
# USE_EMAIL=false  # set true to enable email_agent.py send
```

---

## 5. Error Handling

- **Planner fallback:** If `Runner.run(planner)` returns empty `searches` or raises, fallback to single synthetic `WebSearchItem(reason="fallback", query=query)` so pipeline continues with 1 search.
- **Search fallback:** If any `Runner.run(search, s.query)` raises, capture `f"[Search error for {s.query}: {e}]"` as summary string, continue gather with `return_exceptions=True`.
- **Writer fallback:** If `Runner.run(writer)` raises, return concatenated search summaries joined by `\n\n---\n\n` as markdown report, with `follow_up_questions=[]`.
- **Memory best-effort:** `MemoryStore.save` wrapped in `try/except: log` so research still returns even if DB write fails.

---

## 6. Testing

- **Unit (mocked, no LLM cost):** `tests/test_researcher.py` patches `beau.tools.research.planner.Runner.run`, `search.Runner.run`, `writer.Runner.run` with `AsyncMock` returning `WebSearchPlan`, `str` summaries, `ReportData`; asserts `await research("test")` returns markdown containing query and `follow_up_questions`; tests fallback paths (empty plan, search exception, writer exception).
- **Integration (live, gated):** `uv run python -m beau.tools.researcher "hello"` runs real `OPENROUTER` calls, asserts `len(markdown) > 200` and `follow_ups` present — skipped if `OPENROUTER_API_KEY` not set.
- **API:** `tests/test_api.py` extension `test_research_endpoint` patches `research` and asserts `POST /v1/research` → `200` with `report` key.
- **Existing suite:** Full `uv run pytest tests/ -v` must stay 13 passed + new 3 → 16 passed (existing `beau/core/orchestrator.py` tests mocked, not broken by adding `research_tool`).

---

## 7. Repo Structure (target)

```
BEAU/
├── beau/
│   ├── core/
│   │   ├── config.py  # + HOW_MANY_SEARCHES
│   │   └── orchestrator.py  # + research_tool
│   ├── tools/
│   │   ├── researcher.py  # lean orchestrator (replaces stub)
│   │   ├── actor.py  # still stub — Phase 3
│   │   └── research/
│   │       ├── __init__.py
│   │       ├── planner.py  # WebSearchPlan
│   │       ├── search.py  # Search Agent tools=[] lean
│   │       └── writer.py  # ReportData 1-2 pages
│   ├── api/server.py  # + POST /v1/research
│   └── memory/store.py
├── tests/test_researcher.py
├── docs/superpowers/specs/2026-09-16-beau-researcher-design.md (this file)
└── .env.example
```

---

## 8. Alternatives Considered

- **Approach 1 Direct Port (chosen):** Fastest, exact copy, lean tweaks only, minimal risk.
- **Approach 2 BEAU-Native Lean:** Single-file `researcher.py` with inline `WebSearchItem/ReportData` — cleaner but requires refactoring copy, deferred.
- **Approach 3 Hybrid Search Abstraction:** `SearchProvider` ABC for Tavily/Knowledge — over-engineered for cheap v1, YAGNI.

Approach 1 chosen per user "GO WITH APPROACH 1 THE FASTEST 1" — fastest to demo, aligns with `B` cheap constraint, easy to refactor to Approach 2 later if file count becomes maintenance burden.

---

## 9. Open Questions

- Q1: Keep `email_agent.py` port for `USE_EMAIL=true` optional, or drop email entirely for lean B? Spec assumes dropped unless `USE_EMAIL` set — confirm.
- Q2: Confirm `HOW_MANY_SEARCHES=3` lean is sufficient or need 5 for richer report?

---

*End of spec. Next: `writing-plans` skill to generate `docs/superpowers/plans/2026-09-16-beau-researcher-plan.md` after user approval.*
