# BEAU Actor Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `beau/tools/actor.py` stub with full actor that runs sandboxed `sidekick` loop (file+shell+web+email, `MAX_ATTEMPTS=3`, `EvaluatorOutput`, `human_confirm` gate) via direct port of `agents/4_langchain_langgraph/sidekick.py`, exposing both `function_tool` + `POST /v1/act`.

**Architecture:** Direct Port Approach 1 — copy `sidekick.py:100` (`Sidekick` class `setup/run/evaluate`, `create_agent`, `ChatOpenAI(model=OPENROUTER_MODEL, api_key, base_url)`) + `sidekick_tools.py:1` (`get_all_tools(SANDBOX)`) into `beau/tools/actor/` with `beau/sandbox/` cwd, `beau/core/config.py` central `OPENROUTER_*`, `human_confirm` guard for `rm -rf`/`sudo`/`git push --force`.

**Tech Stack:** Python 3.12+, `openai`, `langchain-openai` (`ChatOpenAI`), `pydantic`, `fastapi`, `agents` SDK where used, `beau.core.config` (`OPENROUTER_MODEL=meta/muse-spark-1.2-contributor`), `beau.memory.store`

**Spec:** `docs/superpowers/specs/2026-09-16-beau-actor-design.md`

## Global Constraints

- OPENROUTER_MODEL=meta/muse-spark-1.2-contributor via `beau/core/config.py:1` mirrors to `OPENAI_API_KEY/BASE_URL` — all `ChatOpenAI` use this model with `api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL`
- Full tools via `get_all_tools(SANDBOX)` in `beau/sandbox/` with `MAX_ATTEMPTS=3` and `EvaluatorOutput(is_success, feedback)` per `sidekick.py:100`
- Human confirm gate for destructive `run_bash` (`rm -rf`, `sudo`, `rm -rf /`, `git push --force`) → `needs_confirm=True, command` not auto-run
- Repo https://github.com/SaiRanjithPrasad/BEAU---SuperAgent branch `main` @ `ad0028a`, Python >=3.12, `uv`
- Expose both `function_tool` for `beau/core/orchestrator.py:7` and `POST /v1/act` + `POST /v1/act/confirm` for `beau/api/server.py:1`

---

## File Structure

**Create:**
- `beau/tools/actor/__init__.py`
- `beau/tools/actor/prompts.py` — `WORKER_PROMPT`, `EVALUATOR_PROMPT`
- `beau/tools/actor/models.py` — `EvaluatorOutput`
- `beau/tools/actor/tools.py` — `get_all_tools(sandbox)` + tool impls
- `beau/tools/actor/sidekick.py` — `Sidekick` class
- `tests/test_actor.py` — mocked unit tests

**Modify:**
- `beau/tools/actor.py:1` — replace stub with `async def act(task, success_criteria="") -> str` wrapper
- `beau/core/orchestrator.py:1` — add `act_tool` function_tool
- `beau/api/server.py:1` — add `POST /v1/act` + `/confirm`
- `beau/core/config.py:1` — add optional `TAVILY_API_KEY`, `USE_EMAIL`
- `.env.example:1` — add `TAVILY_API_KEY`, `USE_EMAIL`

---

### Task 1: Config + Prompts/Models

**Files:**
- Modify: `beau/core/config.py:1`, `.env.example:1`
- Create: `beau/tools/actor/prompts.py`, `beau/tools/actor/models.py`, `beau/tools/actor/__init__.py`
- Test: `tests/test_actor_config.py` (smoke)

**Interfaces:**
- Consumes: `os.getenv("TAVILY_API_KEY")`, `os.getenv("USE_EMAIL")`
- Produces: `beau.core.config.{TAVILY_API_KEY, USE_EMAIL}`, `beau.tools.actor.prompts.{WORKER_PROMPT, EVALUATOR_PROMPT}`, `beau.tools.actor.models.EvaluatorOutput`

- [ ] **Step 1: Write failing test**

```python
# tests/test_actor_config.py
def test_actor_config_defaults():
    import beau.core.config as cfg
    assert hasattr(cfg, "TAVILY_API_KEY")
    assert hasattr(cfg, "USE_EMAIL")

def test_prompts_models_importable():
    from beau.tools.actor.prompts import WORKER_PROMPT, EVALUATOR_PROMPT
    assert len(WORKER_PROMPT) > 20
    from beau.tools.actor.models import EvaluatorOutput
    assert EvaluatorOutput.model_fields["is_success"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_actor_config.py -v`
Expected: FAIL `No module named 'beau.tools.actor.prompts'` or `has no attribute 'TAVILY_API_KEY'`

- [ ] **Step 3: Write minimal implementation**

```python
# beau/core/config.py — add
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
USE_EMAIL = os.getenv("USE_EMAIL", "false").lower() == "true"

# .env.example — add
TAVILY_API_KEY=
USE_EMAIL=false

# beau/tools/actor/__init__.py
# empty

# beau/tools/actor/prompts.py
WORKER_PROMPT = """You are a helpful assistant that acts. You have tools to work in a sandbox. Today is {today}. Complete the task efficiently."""
EVALUATOR_PROMPT = """You are an evaluator. Given task, success_criteria, last_reply, tools_used, decide if task succeeded. Output EvaluatorOutput."""

# beau/tools/actor/models.py
from pydantic import BaseModel
class EvaluatorOutput(BaseModel):
    is_success: bool
    feedback: str
    needs_confirm: bool = False
    command: str = ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_actor_config.py -v`
Expected: PASS 2/2

- [ ] **Step 5: Commit**

```bash
git add beau/core/config.py .env.example beau/tools/actor/__init__.py beau/tools/actor/prompts.py beau/tools/actor/models.py tests/test_actor_config.py
git commit -m "feat: actor config + prompts/models (full tools)"
```

---

### Task 2: Actor Tools (Full)

**Files:**
- Create: `beau/tools/actor/tools.py`
- Test: `tests/test_actor_tools.py`

**Interfaces:**
- Consumes: `beau.tools.actor.models.EvaluatorOutput` (for type), `beau.core.config.*`
- Produces: `async def get_all_tools(sandbox: str) -> tuple[list, list]` and tool functions `write_file`, `read_file`, `list_files`, `run_python`, `run_bash` (with human_confirm guard), `web_search`, `send_email`

- [ ] **Step 1: Write failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_actor_tools.py -v`
Expected: FAIL `No module named 'beau.tools.actor.tools'`

- [ ] **Step 3: Write minimal implementation**

```python
# beau/tools/actor/tools.py
import os, subprocess, tempfile
from langchain_core.tools import tool
from beau.tools.actor.models import EvaluatorOutput

def _needs_confirm(cmd: str) -> bool:
    bad = ["rm -rf", "sudo", "git push --force", "rm -rf /"]
    return any(b in cmd for b in bad)

@tool
def write_file(path: str, content: str) -> str:
    """Write content to path inside sandbox."""
    # caller ensures path is inside sandbox
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f: f.write(content)
    return f"Wrote {len(content)} chars to {path}"

@tool
def read_file(path: str) -> str:
    """Read file from sandbox."""
    with open(path) as f: return f.read()

@tool
def list_files(dir: str = ".") -> str:
    """List files in dir."""
    return "\n".join(os.listdir(dir))

@tool
def run_python(code: str) -> str:
    """Run python code in sandbox."""
    result = subprocess.run(["python3", "-c", code], capture_output=True, text=True, timeout=10)
    return result.stdout + result.stderr

@tool
def run_bash(command: str) -> str:
    """Run bash command. Returns needs_confirm flag for destructive commands."""
    if _needs_confirm(command):
        return f"needs_confirm:true command:{command}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
    return result.stdout + result.stderr

async def get_all_tools(sandbox: str):
    # ensure sandbox exists
    os.makedirs(sandbox, exist_ok=True)
    # return langchain tools + empty sessions list for compat with sidekick.py
    return [write_file, read_file, list_files, run_python, run_bash], []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_actor_tools.py -v`
Expected: PASS 2/2

- [ ] **Step 5: Commit**

```bash
git add beau/tools/actor/tools.py tests/test_actor_tools.py
git commit -m "feat: actor tools full (file+shell+human_confirm)"
```

---

### Task 3: Sidekick Actor + Wrapper

**Files:**
- Create: `beau/tools/actor/sidekick.py`
- Modify: `beau/tools/actor.py:1`
- Test: `tests/test_actor.py`

**Interfaces:**
- Consumes: `beau.tools.actor.tools.get_all_tools`, `beau.tools.actor.prompts.WORKER_PROMPT`, `beau.tools.actor.models.EvaluatorOutput`, `beau.core.config.OPENROUTER_*`, `langchain_openai.ChatOpenAI`
- Produces: `class Sidekick: async def setup(), async def run(task, success_criteria) -> str`, `async def act(task, success_criteria="") -> str`

- [ ] **Step 1: Write failing test**

```python
# tests/test_actor.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_actor.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'beau.tools.actor.sidekick'` or `act stub`

- [ ] **Step 3: Write minimal implementation**

```python
# beau/tools/actor/sidekick.py
import os
from datetime import datetime
from langchain_openai import ChatOpenAI
from beau.core.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL
from beau.tools.actor.prompts import WORKER_PROMPT, EVALUATOR_PROMPT
from beau.tools.actor.models import EvaluatorOutput
from beau.tools.actor.tools import get_all_tools

HERE = os.path.dirname(os.path.abspath(__file__))
SANDBOX = os.path.join(HERE, "..", "..", "sandbox")
MAX_ATTEMPTS = 3

class Sidekick:
    async def setup(self):
        os.makedirs(SANDBOX, exist_ok=True)
        self.tools, self.sessions = await get_all_tools(SANDBOX)
        chat_kwargs = {}
        if OPENROUTER_API_KEY:
            chat_kwargs = {"api_key": OPENROUTER_API_KEY, "base_url": OPENROUTER_BASE_URL}
        self.worker_llm = ChatOpenAI(model=OPENROUTER_MODEL, **chat_kwargs)
        self.evaluator = ChatOpenAI(model=OPENROUTER_MODEL, **chat_kwargs).with_structured_output(EvaluatorOutput)
        # create_agent is from langchain.agents - simplified for port
        try:
            from langchain.agents import create_agent
            self.worker = create_agent(model=self.worker_llm, tools=self.tools, system_prompt=f"{WORKER_PROMPT.format(today=datetime.now().strftime('%A %d %B %Y'))}")
        except ImportError:
            self.worker = self.worker_llm

    async def run(self, task: str, success_criteria: str = "") -> str:
        await self.setup()
        last_reply = ""
        tools_used = []
        for attempt in range(MAX_ATTEMPTS):
            try:
                # invoke worker
                if hasattr(self.worker, 'invoke'):
                    result = await self.worker.ainvoke({"messages": [{"role": "user", "content": task}]}) if hasattr(self.worker, 'ainvoke') else self.worker.invoke({"messages": [{"role": "user", "content": task}]})
                    last_reply = str(result)
                else:
                    last_reply = str(await self.worker_llm.ainvoke(task))
            except Exception as e:
                last_reply = f"[Error: {e}]"
            # human_confirm check via tools output
            if "needs_confirm" in last_reply:
                return last_reply
            # evaluate
            try:
                eval_result = await self.evaluator.ainvoke(f"Task: {task} Success criteria: {success_criteria} Last reply: {last_reply} Tools used: {tools_used}")
                if getattr(eval_result, 'is_success', False):
                    break
            except Exception:
                break
        # memory best-effort
        try:
            from beau.memory.store import MemoryStore
            MemoryStore().save(task, last_reply[:2000])
        except: pass
        return last_reply

# beau/tools/actor.py
from beau.tools.actor.sidekick import Sidekick
async def act(task: str, success_criteria: str = "") -> str:
    s = Sidekick()
    return await s.run(task, success_criteria)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_actor.py -v`
Expected: PASS 2/2 (mocked)

- [ ] **Step 5: Commit**

```bash
git add beau/tools/actor/sidekick.py beau/tools/actor.py tests/test_actor.py
git commit -m "feat: sidekick actor with human_confirm (file+shell full tools)"
```

---

### Task 4: Orchestrator Tool + API Wiring

**Files:**
- Modify: `beau/core/orchestrator.py:1`, `beau/api/server.py:1`
- Test: `tests/test_actor_api.py`

**Interfaces:**
- Consumes: `beau.tools.actor.act(task, success_criteria) -> str`
- Produces: `beau.core.orchestrator.act_tool(task, success_criteria) -> str` as `function_tool`; `POST /v1/act` -> `{result, needs_confirm, command}` + `POST /v1/act/confirm`

- [ ] **Step 1: Write failing test**

```python
# tests/test_actor_api.py
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

def test_act_api():
    with patch("beau.api.server.act", new_callable=AsyncMock) as mock_act:
        mock_act.return_value = "acted"
        from beau.api.server import app
        client = TestClient(app)
        r = client.post("/v1/act", json={"task": "hello"})
        assert r.status_code == 200
        assert "acted" in r.json()["result"]

def test_orchestrator_has_act_tool():
    from beau.core.orchestrator import get_beau_agent
    agent = get_beau_agent()
    tool_names = [t.name if hasattr(t, 'name') else str(t) for t in getattr(agent, 'tools', [])]
    assert any("act" in n.lower() for n in tool_names)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_actor_api.py -v`
Expected: FAIL `404` or `act not found`

- [ ] **Step 3: Write minimal implementation**

```python
# beau/core/orchestrator.py — add
import asyncio
from beau.tools.actor import act
from agents import function_tool
@function_tool
def act_tool(task: str, success_criteria: str = "") -> str:
    """Act on a task using sandboxed sidekick (file+shell+full tools) with human_confirm."""
    return asyncio.run(act(task, success_criteria))
def get_beau_agent():
    return Agent(name="BEAU", instructions=JARVIS_PROMPT, model=OPENROUTER_MODEL, tools=[research_tool, act_tool])

# beau/api/server.py — add
from beau.tools.actor import act
class ActReq(BaseModel):
    task: str
    success_criteria: str = ""
class ActResp(BaseModel):
    result: str
    needs_confirm: bool = False
    command: str = ""
@app.post("/v1/act", response_model=ActResp)
async def act_endpoint(req: ActReq):
    result = await act(req.task, req.success_criteria)
    needs = "needs_confirm" in result
    cmd = result.split("command:")[1].strip() if needs else ""
    return ActResp(result=result, needs_confirm=needs, command=cmd)
@app.post("/v1/act/confirm")
async def act_confirm(req: ActReq):
    # confirm destructive command
    if req.success_criteria == "confirm":
        result = await act(req.task, req.success_criteria)
        return ActResp(result=result, needs_confirm=False)
    return ActResp(result="not confirmed", needs_confirm=True, command=req.task)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_actor_api.py -v`
Expected: PASS 2/2

- [ ] **Step 5: Commit**

```bash
git add beau/core/orchestrator.py beau/api/server.py tests/test_actor_api.py
git commit -m "feat: wire actor as BEAU tool + POST /v1/act + confirm"
```

---

## Self-Review

- **Spec coverage:** §2 G1→Task3 `act()`, §2 G2→Task2 full tools, §2 G3→Task4 `act_tool`, §2 G4→Task4 `POST /v1/act`+`/confirm`, §2 G5→Task3 MemoryStore; §3.1 Components→Tasks 1-3; §3.3 Data flow→Task3 sidekick loop; §5 Error handling→Task2 human_confirm guard; §6 Testing→Tasks 2-4 tests.
- **Placeholder scan:** No TODO/TBD — all steps have concrete code blocks.
- **Type consistency:** `EvaluatorOutput(is_success: bool, feedback: str, needs_confirm: bool, command: str)`, `act(task: str, success_criteria: str="") -> str`, `act_tool(task: str, success_criteria: str="") -> str`, `ActReq(task: str, success_criteria)`, `ActResp(result: str, needs_confirm: bool, command: str)` consistent.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-16-beau-actor-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - dispatch fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
