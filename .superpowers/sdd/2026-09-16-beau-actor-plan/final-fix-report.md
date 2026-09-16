# Final Fix Report — 9494988 findings (4 Important + 2 Minor)

**Base:** 9494988
**Date:** 2026-09-16
**Diff reviewed:** review-befaa62..9494988.diff

## Findings fixed

1. **Confirm flow re-triggers guard** `beau/api/server.py:58-64` + `beau/tools/actor/__init__.py:3` + `beau/tools/actor/sidekick.py:53-59`
   - Before: `act_confirm` called `await act(req.task, "confirm")` which re-entered `run_bash` guard via `_needs_confirm`, returning `needs_confirm:true` again and never executing.
   - Fix: Added `confirmed: bool = False` param to `act(task, success_criteria, confirmed)` (`beau/tools/actor/__init__.py:3`) and `Sidekick.run(task, success_criteria, confirmed)` (`beau/tools/actor/sidekick.py:53`). When `confirmed=True`, `run` bypasses LLM/tools and executes `subprocess.run(task, shell=True)` directly (`beau/tools/actor/sidekick.py:55-59`). `act_confirm` now calls `await act(req.task, req.success_criteria, confirmed=True)` when `success_criteria=="confirm"` and returns `needs_confirm=False` (`beau/api/server.py:58-63`). Verified via `TestClient` mock: `act` called with `confirmed=True`, confirm endpoint returns `needs_confirm=False`.

2. **create_agent fallback loses tool calling** `beau/tools/actor/sidekick.py:14-24,34-51`
   - Before: `from langchain.agents import create_agent` always fails in this env, `_create_agent=None`, fallback in `setup()` set `self.worker = self.worker_llm` bare LLM with no tools.
   - Fix: Primary import now tries `langchain.agents` then `langchain_core.agents` (`beau/tools/actor/sidekick.py:14-20`). In `setup()`, fallback retains tool calling via `self.worker_llm.bind_tools(self.tools)` when `bind_tools` exists (`beau/tools/actor/sidekick.py:46-51`). Also handles `create_agent is None` by trying second import before falling back. Verified: with `create_agent=None` mock, `ChatOpenAI.bind_tools` called and `worker == bound_worker`.

3. **web_search stub even with TAVILY_API_KEY** `beau/tools/actor/tools.py:41-65`
   - Before: When `TAVILY_API_KEY` set, returned `f"web_search result for: {query} (TAVILY_API_KEY set)"` stub without HTTP call.
   - Fix: Real `httpx.post("https://api.tavily.com/search", json={"api_key": TAVILY_API_KEY, "query": query, "max_results": 5, "search_depth": "basic"}, timeout=10)` with `raise_for_status`, JSON parse, and formatting of top 3 results as `title: content (url)` (`beau/tools/actor/tools.py:44-64`). Preserves `try/except` for missing `httpx`. Verified via `patch("httpx.post")` mock returning `{"results": [{"title":"T1",...}]}` — output contains titles/urls; without key returns stub.

4. **asyncio.run in function_tool fails inside running loop** `beau/core/orchestrator.py:15-18`
   - Before: `research_tool`/`act_tool` used bare `asyncio.run(coro)` which raises `RuntimeError: asyncio.run cannot be called from a running event loop` when invoked from async context (e.g., Agents SDK).
   - Fix: Added `_run_async(coro)` helper (`beau/core/orchestrator.py:10-20`) that checks `asyncio.get_running_loop()`; if loop running, delegates to `ThreadPoolExecutor().submit(asyncio.run, coro).result()` else `asyncio.run(coro)`. Both tools now call `_run_async` (`beau/core/orchestrator.py:23,28`). Verified both outside and inside `asyncio.run` context return correctly.

## Minor findings fixed

5. **Sandbox traversal not enforced** `beau/tools/actor/tools.py:1-35`
   - Before: `write_file`/`read_file`/`list_files` opened any path, caller comment said "caller ensures" but no check; `path.contains("..")` or absolute `/etc/passwd` escaped sandbox.
   - Fix: Added `SANDBOX_DEFAULT`/`_SANDBOX` globals, `_resolve(path)` (absolute vs sandbox-relative), `_is_within_sandbox(path)` via `os.path.commonpath` (`beau/tools/actor/tools.py:4-20`). `get_all_tools(sandbox)` now sets global `_SANDBOX = abspath(sandbox)` (`beau/tools/actor/tools.py:71-72`). Each tool checks `_is_within_sandbox` and returns `error: path traversal blocked: {path} not inside sandbox {SANDBOX}` if outside; `write_file`/`list_files` resolve target before `open`/`listdir`. Verified: `write_file ../../etc/passwd` blocked, `write_file inside_test.txt` succeeds at `/.../beau/sandbox/inside_test.txt`, `list_files /tmp` blocked.

6. **tools_used never populated** `beau/tools/actor/sidekick.py:90-135`
   - Before: `tools_used = []` initialized but never appended; evaluator prompt saw empty list.
   - Fix: After `worker.ainvoke`/`invoke`, extracts `tool_calls` from `result["messages"]` or `result.messages` (dict or object), handles both `dict` and attribute forms and `result.tool_calls` fallback, appends string names to `tools_used` (`beau/tools/actor/sidekick.py:90-135`). Verified dict-form mock with `tool_calls=[{"name":"write_file"}]` populates `Tools used: ['write_file']` in evaluator prompt.

## Tests

```
$ uv run pytest tests/ -v
30 passed (test_actor x2, test_actor_api x2, test_actor_config x2, test_actor_tools x2, test_api, test_config x3, test_fish_audio x2, test_memory, test_orchestrator x2, test_researcher x3, test_researcher_api x2, test_researcher_planner x3, test_scaffold x3, test_stt x2)
```

Manual checks:
- `run_bash rm -rf /tmp/test` -> `needs_confirm:true`, `act(..., confirmed=True)` bypasses and echoes.
- `POST /v1/act` returns `needs_confirm:true`, `POST /v1/act/confirm` with `confirm` returns `needs_confirm:false`.
- `httpx.post` called with `api.tavily.com/search` + api_key when key set.
- `_run_async` inside `asyncio.run` uses ThreadPoolExecutor fallback correctly.
- `write_file`/`read_file` traversal blocked.

## Commits

Single fix commit on top of 9494988 covering all 4 Important + 2 Minor findings.
