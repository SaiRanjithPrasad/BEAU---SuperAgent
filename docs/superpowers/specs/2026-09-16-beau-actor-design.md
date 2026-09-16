# BEAU Actor Phase 3 — Design Spec (Approach 1 Direct Port Full Tools + Human Confirm)

**Date:** 2026-09-16  
**Repo:** https://github.com/SaiRanjithPrasad/BEAU---SuperAgent @ `5c49f22`  
**Status:** Draft → Awaiting review before `writing-plans`  
**Parent spec:** `docs/superpowers/specs/2026-09-16-beau-superagent-design.md` §3.2 Actor, Phase 3  
**Related plan:** `docs/superpowers/plans/2026-09-16-beau-superagent-plan.md` Task 8 stubs → replaced here; Phase 2 researcher `2b7689d`/`63279e5` done  
**Approach:** **1 Direct Port Full (Fastest)** — copy `agents/4_langchain_langgraph/sidekick.py:30` + `sidekick_tools.py:1` verbatim with `human_confirm` gate, `MAX_ATTEMPTS=3`, `EvaluatorOutput`, full tools (file+shell+web+email)  
**Priority:** `C Acts` full tools per brainstorming 2026-09-16 (file+shell+web+email > lean)

---

## 1. Summary

Replace `beau/tools/actor.py:1` stub (`"[Act stub for: {task}] — Phase 3"`) with full actor that reuses exactly `agents/4_langchain_langgraph/sidekick.py:30` pattern (`OPENROUTER` `ChatOpenAI(model=OPENROUTER_MODEL, api_key, base_url)`, `MAX_ATTEMPTS=3`, `create_agent(worker, tools, system_prompt, middleware, checkpointer)`, `evaluator.with_structured_output(EvaluatorOutput)`), centralized on `beau/core/config.py:1` (`OPENROUTER_MODEL=meta/muse-spark-1.2-contributor`, `OPENAI_*` mirroring). Full tools via `get_all_tools(SANDBOX)` (file, shell, web, email) with `human_confirm` gate for destructive `run_bash` (`rm -rf`, `sudo`, `git push --force`). Exposes both `function_tool` for `beau/core/orchestrator.py:7` BEAU handoff and `POST /v1/act` + `POST /v1/act/confirm` in `beau/api/server.py:1`.

---

## 2. Goals / Non-Goals

**Goals:**
- G1: `act(task: str, success_criteria: str = "") -> str` runs sandboxed `sidekick` loop `setup() → tools → worker → evaluate` up to 3 attempts, returning final reply.
- G2: Full tools `get_all_tools(SANDBOX)` usable in `beau/sandbox/` with `human_confirm` gate (`needs_confirm`).
- G3: Expose as `function_tool` so BEAU `Agent(name="BEAU")` auto-routes "act on X".
- G4: Expose `POST /v1/act {task, success_criteria}` + `POST /v1/act/confirm {command, confirm}` for explicit demo.
- G5: Persist via `checkpointer` (`beau/memory` pattern) and `MemoryStore.save`.

**Non-Goals:**
- No autonomous scheduling (`D`), no multi-agent delegation (`E`) — single actor loop.
- No live deployment beyond local `uv run` (Gradio `beau/ui/app.py:1` already).

**Success criteria:**
- `uv run pytest tests/test_actor.py -v` mocked 3/3 passes (write, shell, needs_confirm).
- `uv run python -m beau.tools.actor "create file hello.txt with hello"` creates `beau/sandbox/hello.txt` with `hello` when live (mocked in CI) and `evaluator` marks success.
- `curl -X POST http://localhost:8000/v1/act -d '{"task":"list files"}'` → `{"result": "...", "needs_confirm": false}`; `rm -rf` task → `{"needs_confirm": true, "command": "rm -rf ..."}`
- BEAU chat "act: create a python script that prints hi" triggers `act_tool` and returns result.

---

## 3. Architecture

### 3.1 Components

| Component | Path | Source | Responsibility |
|-----------|------|--------|----------------|
| **Sidekick Actor** | `beau/tools/actor/sidekick.py` | Copy `agents/4_langchain_langgraph/sidekick.py:30` | `Sidekick` class `__init__`, `async setup()`, `async run(task, success_criteria)`, `async evaluate()`, `human_confirm(command) -> bool` gate; `HERE = os.path.dirname(...)`, `SANDBOX = beau/sandbox`, `MAX_ATTEMPTS=3`, `OPENROUTER` `ChatOpenAI` mirroring |
| **Tools** | `beau/tools/actor/tools.py` | Copy `sidekick_tools.py:1` | `async def get_all_tools(sandbox: str) -> tuple[list[Tool], list[session]]` → file `write_file`, `read_file`, `list_files`, `run_python`, `run_bash` (with `human_confirm` check), `web_search` (Tavily if `TAVILY_API_KEY` else stub), `send_email` (stub if `USE_EMAIL=false`) |
| **Prompts** | `beau/tools/actor/prompts.py` | `sidekick.py:WORKER_PROMPT` + `EVALUATOR_PROMPT` | `WORKER_PROMPT = "You are a helpful assistant that acts..."`, `EVALUATOR_PROMPT` for `EvaluatorOutput` |
| **Models** | `beau/tools/actor/models.py` | `sidekick.py:EvaluatorOutput` | `class EvaluatorOutput(BaseModel): is_success: bool, feedback: str, needs_confirm: bool = False, command: str = ""` |
| **Wrapper** | `beau/tools/actor.py:1` | Replaces stub | `async def act(task: str, success_criteria: str = "") -> str: s=Sidekick(); await s.setup(); return await s.run(task, success_criteria)` |
| **Tool** | `beau/core/orchestrator.py:7` | Modify | Add `@function_tool def act_tool(task: str, success_criteria: str="") -> str: return asyncio.run(act(task, success_criteria))` and `tools=[research_tool, act_tool]` |
| **API** | `beau/api/server.py:1` | Modify | Add `class ActReq(BaseModel): task: str; success_criteria: str = ""` `class ActResp(BaseModel): result: str; needs_confirm: bool; command: str = ""` `POST /v1/act` + `POST /v1/act/confirm` |

### 3.2 Files

**Create:**
- `beau/tools/actor/__init__.py`
- `beau/tools/actor/sidekick.py`
- `beau/tools/actor/tools.py`
- `beau/tools/actor/prompts.py`
- `beau/tools/actor/models.py`
- `tests/test_actor.py`

**Modify:**
- `beau/tools/actor.py:1` (wrapper)
- `beau/core/orchestrator.py:1` (add `act_tool`)
- `beau/api/server.py:1` (add `POST /v1/act` + `/confirm`)
- `beau/core/config.py:1` (ensure `OPENROUTER_*` already, add `TAVILY_API_KEY` optional)

### 3.3 Data Flow

```
User "act: create file X" ─┬─ via BEAU chat → act_tool(task) ─┐
                           └─ via POST /v1/act {task} ────────┤
                                                            ▼
                                                     act(task, success_criteria)
                                                            │
                                                    Sidekick.setup()
                                                    mkdir SANDBOX, get_all_tools(SANDBOX)
                                                    create_agent(worker, tools, WORKER_PROMPT)
                                                    evaluator = ChatOpenAI(OPENROUTER_MODEL).with_structured_output(EvaluatorOutput)
                                                            │
                                            ┌───────────────┼───────────────┐
                                            ▼               │               ▼
                                       attempt 1..3    (human_confirm)   evaluate
                                    worker.invoke(task) → tools_used → EvaluatorOutput
                                            │               │               │
                                            │         if "rm -rf" in cmd → needs_confirm=True → return
                                            │               │
                                            └────── if is_success break else feedback → retry
                                                            │
                                                            ▼
                                                     return last_reply
                                                     MemoryStore.save(task, last_reply)
```

Spec §4.2 cheap: actor loop uses `OPENROUTER_MODEL` with `ChatOpenAI(api_key, base_url)` per `sidekick.py:100` pattern.

---

## 4. Configuration

Reuse `beau/core/config.py:1` `OPENROUTER_*`, add optional:

```python
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
USE_EMAIL = os.getenv("USE_EMAIL", "false").lower() == "true"
```

`.env.example` add:

```
TAVILY_API_KEY=
USE_EMAIL=false
```

---

## 5. Error Handling

- **Destructive shell:** `run_bash` checks `cmd in ["rm -rf", "sudo", "rm -rf /", "git push --force"]` → return `ActResp(result="", needs_confirm=True, command=cmd)` without execution, wait for `POST /v1/act/confirm`.
- **Tool error:** File not found, python error → `EvaluatorOutput(is_success=False, feedback=error)` → retry up to 3.
- **Evaluator failure:** If `with_structured_output` raises, fallback to `last_reply` as success.

---

## 6. Testing

- **Unit (mocked, no live FS):** `tests/test_actor.py` patches `get_all_tools`, `create_agent`, `ChatOpenAI`, `Runner`/`evaluator`; asserts `await act("create file")` calls `write_file` tool, `await act("rm -rf /tmp")` → `needs_confirm=True`, `await act("run python")` success.
- **Integration (live, gated):** `uv run python -m beau.tools.actor "create file hello.txt"` creates `beau/sandbox/hello.txt` with live `OPENROUTER` — skipped if no key.
- **API:** `tests/test_api.py` extension `test_act_endpoint` patches `act` and asserts `POST /v1/act` → `200` with `result`, `test_act_confirm` asserts confirm flow.
- **Existing suite:** Full `uv run pytest tests/ -v` must stay 22 passed + new 3 → 25 passed.

---

## 7. Repo Structure (target)

```
BEAU/
├── beau/
│   ├── core/
│   │   └── orchestrator.py  # + act_tool
│   ├── tools/
│   │   ├── actor.py  # wrapper
│   │   ├── actor/
│   │   │   ├── __init__.py
│   │   │   ├── sidekick.py  # Sidekick class
│   │   │   ├── tools.py  # get_all_tools
│   │   │   ├── prompts.py
│   │   │   └── models.py  # EvaluatorOutput
│   │   └── research/  # Phase 2 done
│   └── api/server.py  # + POST /v1/act
├── tests/test_actor.py
├── docs/superpowers/specs/2026-09-16-beau-actor-design.md (this file)
└── .env.example
```

---

## 8. Alternatives Considered

- **Approach 1 Direct Port Full (chosen):** Fastest, exact copy, full tools, human confirm via one guard.
- **Approach 2 BEAU-Native Lean:** Single-file `actor.py` lean — cleaner but requires refactoring copy, deferred.
- **Approach 3 MCP Trading-Floor Style:** `6_mcp/backend/trading_floor.py:1` MCP — heavy for `C` MVP, YAGNI.

Approach 1 chosen per user "LETS DO FULL TOOLS" + fastest (like Phase 2) — full reuse, minimal risk.

---

## 9. Open Questions

- Q1: Confirm `TAVILY_API_KEY` source (add to `.env` now or stub web_search for cheap)?
- Q2: Confirm `USE_EMAIL` sender config (`PUSHOVER` vs `send_email`) for `send_email` tool?

---

*End of spec. Next: `writing-plans` skill to generate `docs/superpowers/plans/2026-09-16-beau-actor-plan.md` after user approval.*
