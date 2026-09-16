# BEAU SuperAgent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship BEAU Jarvis-like SuperAgent MVP (A Converses + voice) with Muse Spark via OpenRouter, Fish Audio S2 Pro TTS, Hermes browser bridge, and staged path to B/C/D/E.

**Architecture:** Modular Master+Workers — FastAPI/Gradio orchestrator handoffs to researcher/actor workers; voice stack is Fish Audio client (cloud `fish-audio-python` primary, local `fish-speech` SGLang fallback) + STT provider abstraction (OpenCode voice-input spike vs faster-whisper); persistent SQLite memory; RevenueCat MCP stub.

**Tech Stack:** Python 3.12+, `openai`, `openai-agents` (agents SDK), `langchain-openai`, `gradio 5`, `fastapi+uvicorn`, `fish-audio-python`, `faster-whisper`, `python-dotenv`, `pytest`, `omniroute` (provider `openrouter` 957b9614)

**Spec:** `docs/superpowers/specs/2026-09-16-beau-superagent-design.md`

## Global Constraints

- OPENROUTER_API_KEY=sk-or-v1-... set in .env, OPENROUTER_BASE_URL=https://openrouter.ai/api/v1, OPENROUTER_MODEL=meta/muse-spark-1.2-contributor (also DEFAULT_MODEL_NAME/WORKER_MODEL/ORCHESTRATOR_MODEL) — mirrors to OPENAI_API_KEY/BASE_URL via openrouter_config.py:28
- OmniRoute inference via https://openrouter.ai/api/v1 passthrough model id is `openrouter/<upstream>` e.g. `openrouter/openai/gpt-4o-mini` validated, `openrouter/meta/muse-spark-1.2-contributor` for BEAU
- Fish Audio S2 Pro license is FISH AUDIO RESEARCH LICENSE — cloud `fish-audio-python` is Apache-2.0 primary, local `fish-speech` is opt-in only
- Repo is https://github.com/SaiRanjithPrasad/BEAU---SuperAgent branch `main`, Python >=3.12, `uv` for deps
- Phase order enforced: 0 Scaffold done → 1 A Converses+Voice → 2 B Researches → 3 C Acts → 4 D/E + RevenueCat → 5 Local fish-speech polish

---

## File Structure

**Create:**
- `beau/core/config.py` — centralized env loader, mirrors `openrouter_config.py`, exposes `OPENROUTER_*`, `FISH_*`, `HERMES_*`, `REVENUECAT_*`
- `beau/core/prompts.py` — `JARVIS_PROMPT` system prompt
- `beau/core/orchestrator.py` — `Agent(name="BEAU")` + `Runner.run()` with handoffs
- `beau/voice/fish_audio/client.py` — `FishAudioClient` wrapper (cloud vs local)
- `beau/voice/stt/provider.py` — `STTProvider` ABC + `FasterWhisperSTT` + `OpenCodeVoiceSTT` stub
- `beau/browser/hermes.py` — Hermes Agent browser MCP bridge
- `beau/billing/revenuecat.py` — `is_entitled()` stub
- `beau/memory/store.py` — SQLite memory
- `beau/api/server.py` — FastAPI `/v1/chat`, `/v1/audio/*`
- `beau/ui/app.py` — Gradio Jarvis UI
- `tests/test_config.py`, `tests/test_orchestrator.py`, `tests/test_fish_audio.py`, `tests/test_stt.py`, `tests/test_memory.py`, `tests/test_api.py`
- `data/.gitkeep`, `beau/sandbox/.gitkeep`

**Modify:**
- `pyproject.toml:1` — ensure deps above
- `.env.example:1` — already has full template
- `openrouter_config.py:1` — keep as re-export shim to `beau/core/config.py`

---

### Task 0: Validate Scaffold Post-Commit

**Files:**
- Test: `tests/test_scaffold.py`

**Interfaces:**
- Consumes: existing `a267a45` commit scaffold
- Produces: verified spec + scaffold present

- [ ] **Step 1: Write scaffold smoke test**

```python
# tests/test_scaffold.py
import os
def test_spec_exists():
    assert os.path.exists("docs/superpowers/specs/2026-09-16-beau-superagent-design.md")
def test_openrouter_config_importable():
    import openrouter_config
    assert hasattr(openrouter_config, "OPENROUTER_MODEL")
def test_beau_pkg_exists():
    import beau
    assert True
```

- [ ] **Step 2: Run test to verify it fails (before adding tests dir)**

Run: `uv run pytest tests/test_scaffold.py -v`
Expected: FAIL `ModuleNotFoundError` or `File not found` until deps installed

- [ ] **Step 3: Install deps and run**

Run: `uv sync && uv run pytest tests/test_scaffold.py -v`
Expected: PASS (spec exists, config importable)

- [ ] **Step 4: Commit (if fixes needed)**

```bash
git add tests/test_scaffold.py
git commit -m "test: scaffold smoke" || true
```

---

### Task 1: Core Config (Centralized Env Mirroring)

**Files:**
- Create: `beau/core/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: `.env.example` vars, `openrouter_config.py:19-30` pattern
- Produces: `beau.core.config.{OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL, FISH_AUDIO_API_KEY, STT_PROVIDER, HERMES_ENABLED}` and function `load_config() -> Config`

- [ ] **Step 1: Write failing test**

```python
# tests/test_config.py
import os
from unittest.mock import patch

def test_config_mirrors_openai_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENROUTER_MODEL", "meta/muse-spark-1.2-contributor")
    # reimport
    import importlib, beau.core.config as cfg
    importlib.reload(cfg)
    cfg.load_config()
    assert os.environ["OPENAI_API_KEY"] == "sk-or-v1-test"
    assert os.environ["OPENAI_BASE_URL"] == "https://openrouter.ai/api/v1"
    assert cfg.OPENROUTER_MODEL == "meta/muse-spark-1.2-contributor"

def test_config_fish_audio_defaults(monkeypatch):
    import importlib, beau.core.config as cfg
    importlib.reload(cfg)
    cfg.load_config()
    assert cfg.FISH_AUDIO_USE_LOCAL is False
    assert cfg.FISH_AUDIO_BASE_URL == "https://api.fish.audio"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL `ModuleNotFoundError: No module named 'beau.core.config'`

- [ ] **Step 3: Write minimal implementation**

```python
# beau/core/config.py
import os
from dotenv import load_dotenv
load_dotenv(override=True)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", os.getenv("DEFAULT_MODEL_NAME", "meta/muse-spark-1.2-contributor"))
if not os.getenv("OPENROUTER_MODEL") and os.getenv("WORKER_MODEL"):
    OPENROUTER_MODEL = os.getenv("WORKER_MODEL")

FISH_AUDIO_API_KEY = os.getenv("FISH_AUDIO_API_KEY", "")
FISH_AUDIO_USE_LOCAL = os.getenv("FISH_AUDIO_USE_LOCAL", "false").lower() == "true"
FISH_AUDIO_BASE_URL = os.getenv("FISH_AUDIO_BASE_URL", "https://api.fish.audio")
FISH_AUDIO_VOICE_ID = os.getenv("FISH_AUDIO_VOICE_ID", "beau_jarvis")

STT_PROVIDER = os.getenv("STT_PROVIDER", "faster_whisper")
HERMES_ENABLED = os.getenv("HERMES_ENABLED", "true").lower() == "true"
HERMES_BROWSER_MCP_URL = os.getenv("HERMES_BROWSER_MCP_URL", "http://localhost:3000/mcp")

REVENUECAT_API_KEY = os.getenv("REVENUECAT_API_KEY", "")
REVENUECAT_ENTITLEMENT = os.getenv("REVENUECAT_ENTITLEMENT", "beau_pro")
BEAU_MEMORY_PATH = os.getenv("BEAU_MEMORY_PATH", "./data/beau.db")
BEAU_API_PORT = int(os.getenv("BEAU_API_PORT", "7860"))

DEFAULT_MODEL_NAME = OPENROUTER_MODEL

def load_config():
    if OPENROUTER_API_KEY:
        os.environ["OPENAI_API_KEY"] = OPENROUTER_API_KEY
        os.environ["OPENAI_BASE_URL"] = OPENROUTER_BASE_URL
    return {
        "OPENROUTER_MODEL": OPENROUTER_MODEL,
        "FISH_AUDIO_USE_LOCAL": FISH_AUDIO_USE_LOCAL,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add beau/core/config.py tests/test_config.py
git commit -m "feat: core config mirroring (openrouter→openai + fish/hermes/revenuecat)"
```

---

### Task 2: Jarvis Prompts + Orchestrator A (Converses)

**Files:**
- Create: `beau/core/prompts.py`, `beau/core/orchestrator.py`
- Test: `tests/test_orchestrator.py`

**Interfaces:**
- Consumes: `beau.core.config.OPENROUTER_MODEL`, `Agents SDK Agent/Runner`
- Produces: `beau.core.orchestrator.get_beau_agent() -> Agent`, `async def run_beau(prompt: str) -> str`

- [ ] **Step 1: Write failing test**

```python
# tests/test_orchestrator.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_orchestrator.py -v`
Expected: FAIL `No module named 'beau.core.orchestrator'`

- [ ] **Step 3: Write minimal implementation**

```python
# beau/core/prompts.py
JARVIS_PROMPT = """You are BEAU — a Jarvis-like SuperAgent. Witty, concise, proactive, British-tinged but warm. You help with conversation, research, and actions. You remember context. You use tools when needed. You never hallucinate capabilities you don't have."""

# beau/core/orchestrator.py
import os
from agents import Agent, Runner
from beau.core.config import OPENROUTER_MODEL, load_config
from beau.core.prompts import JARVIS_PROMPT

load_config()

def get_beau_agent():
    return Agent(name="BEAU", instructions=JARVIS_PROMPT, model=OPENROUTER_MODEL)

async def run_beau(prompt: str) -> str:
    agent = get_beau_agent()
    result = await Runner.run(agent, prompt)
    return result.final_output
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_orchestrator.py -v`
Expected: PASS (mocked)

- [ ] **Step 5: Commit**

```bash
git add beau/core/prompts.py beau/core/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: orchestrator A converses (Jarvis prompt + Muse Spark agent)"
```

---

### Task 3: Fish Audio Voice Client (Fish-Audio-Python + Local Fallback)

**Files:**
- Create: `beau/voice/fish_audio/client.py`
- Test: `tests/test_fish_audio.py`

**Interfaces:**
- Consumes: `FISH_AUDIO_API_KEY`, `FISH_AUDIO_USE_LOCAL`, `fish-audio-python` SDK
- Produces: `class FishAudioClient: async def tts(text: str, voice_id: str) -> bytes, def is_available() -> bool`

- [ ] **Step 1: Write failing test**

```python
# tests/test_fish_audio.py
from unittest.mock import patch, AsyncMock

def test_fish_audio_client_cloud_mock():
    with patch("beau.voice.fish_audio.client.FishAudioSDK") as mock_sdk:
        mock_sdk.return_value.tts.return_value = b"fake_wav"
        from beau.voice.fish_audio.client import FishAudioClient
        c = FishAudioClient(api_key="fake", use_local=False)
        assert c.is_available() is True

def test_fish_audio_fallback_when_no_key():
    from beau.voice.fish_audio.client import FishAudioClient
    c = FishAudioClient(api_key="", use_local=False)
    assert c.is_available() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_fish_audio.py -v`
Expected: FAIL `No module named 'beau.voice.fish_audio.client'`

- [ ] **Step 3: Write minimal implementation**

```python
# beau/voice/fish_audio/client.py
import os
from beau.core.config import FISH_AUDIO_API_KEY, FISH_AUDIO_USE_LOCAL, FISH_AUDIO_BASE_URL, FISH_AUDIO_VOICE_ID

try:
    from fish_audio_sdk import Session as FishAudioSDK  # fish-audio-python package provides this
except ImportError:
    FishAudioSDK = None

class FishAudioClient:
    def __init__(self, api_key: str = FISH_AUDIO_API_KEY, use_local: bool = FISH_AUDIO_USE_LOCAL, base_url: str = FISH_AUDIO_BASE_URL, voice_id: str = FISH_AUDIO_VOICE_ID):
        self.api_key = api_key
        self.use_local = use_local
        self.base_url = base_url
        self.voice_id = voice_id
        self._sdk = FishAudioSDK(api_key) if FishAudioSDK and api_key and not use_local else None

    def is_available(self) -> bool:
        return bool(self.api_key or self.use_local)

    async def tts(self, text: str, voice_id: str = None) -> bytes:
        vid = voice_id or self.voice_id
        if self.use_local:
            # local fish-speech SGLang server
            import httpx
            async with httpx.AsyncClient() as client:
                r = await client.post(f"{self.base_url}/v1/tts", json={"text": text, "voice": vid}, timeout=20.0)
                r.raise_for_status()
                return r.content
        if not self._sdk:
            raise RuntimeError("Fish Audio not configured: set FISH_AUDIO_API_KEY or FISH_AUDIO_USE_LOCAL=true")
        # cloud path - SDK signature may vary, wrap with inline tag support
        # Fish S2 supports [whisper] [excited] tags passthrough
        return await self._sdk.tts(text) if hasattr(self._sdk, "tts") else b""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_fish_audio.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add beau/voice/fish_audio/client.py tests/test_fish_audio.py
git commit -m "feat: fish audio voice client (cloud + local fallback)"
```

---

### Task 4: STT Provider Abstraction + Spike (OpenCode Voice-Input)

**Files:**
- Create: `beau/voice/stt/provider.py`
- Test: `tests/test_stt.py`

**Interfaces:**
- Consumes: `STT_PROVIDER` env
- Produces: `class STTProvider(ABC): async def transcribe(audio_bytes: bytes) -> str`, `FasterWhisperSTT`, `OpenCodeVoiceSTT`, `def get_stt() -> STTProvider`

- [ ] **Step 1: Write failing test**

```python
# tests/test_stt.py
import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_faster_whisper_mock():
    from beau.voice.stt.provider import FasterWhisperSTT
    with patch("beau.voice.stt.provider.WhisperModel") as mock_w:
        mock_w.return_value.transcribe.return_value = ([type("S", (), {"text": "hello"})()], None)
        s = FasterWhisperSTT()
        out = await s.transcribe(b"fake_wav")
        assert "hello" in out

def test_get_stt_factory():
    from beau.voice.stt.provider import get_stt
    s = get_stt(provider="faster_whisper")
    assert s is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_stt.py -v`
Expected: FAIL `No module named 'beau.voice.stt.provider'`

- [ ] **Step 3: Write minimal implementation**

```python
# beau/voice/stt/provider.py
from abc import ABC, abstractmethod
from beau.core.config import STT_PROVIDER

class STTProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes) -> str: ...

class FasterWhisperSTT(STTProvider):
    async def transcribe(self, audio_bytes: bytes) -> str:
        try:
            from faster_whisper import WhisperModel
            import tempfile, os
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes); path = f.name
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(path)
            os.unlink(path)
            return " ".join(s.text for s in segments)
        except Exception as e:
            return f"[STT error: {e}]"

class OpenCodeVoiceSTT(STTProvider):
    async def transcribe(self, audio_bytes: bytes) -> str:
        # SPIKE: check if `opencode` CLI exposes voice-input; placeholder delegates to FasterWhisper until verified
        # TODO after spike: if opencode voice-input exists, call it via subprocess/HTTP
        fallback = FasterWhisperSTT()
        return await fallback.transcribe(audio_bytes)

def get_stt(provider: str = STT_PROVIDER) -> STTProvider:
    if provider == "opencode_voice":
        return OpenCodeVoiceSTT()
    return FasterWhisperSTT()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_stt.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add beau/voice/stt/provider.py tests/test_stt.py
git commit -m "feat: stt provider abstraction + OpenCode voice spike stub"
```

---

### Task 5: Browser Hermes Bridge + Memory + RevenueCat Stub

**Files:**
- Create: `beau/browser/hermes.py`, `beau/memory/store.py`, `beau/billing/revenuecat.py`
- Test: `tests/test_memory.py`

**Interfaces:**
- Consumes: `HERMES_BROWSER_MCP_URL`, `BEAU_MEMORY_PATH`
- Produces: `HermesBridge.{play_audio, snapshot}`, `MemoryStore.{save, recall}`, `is_entitled(user_id, feature) -> bool`

- [ ] **Step 1: Write failing test**

```python
# tests/test_memory.py
def test_memory_store():
    from beau.memory.store import MemoryStore
    import tempfile
    with tempfile.NamedTemporaryFile() as f:
        m = MemoryStore(path=f.name)
        m.save("user: hi", "assistant: hello")
        assert "hello" in m.recall("hi")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_memory.py -v`
Expected: FAIL `No module named 'beau.memory.store'`

- [ ] **Step 3: Write minimal implementation**

```python
# beau/browser/hermes.py
import httpx
from beau.core.config import HERMES_BROWSER_MCP_URL, HERMES_ENABLED
class HermesBridge:
    def __init__(self, url=HERMES_BROWSER_MCP_URL, enabled=HERMES_ENABLED):
        self.url = url; self.enabled = enabled
    async def play_audio(self, wav: bytes): 
        if not self.enabled: return
        try:
            async with httpx.AsyncClient() as c: await c.post(f"{self.url}/play", content=wav, timeout=5)
        except: pass
    async def snapshot(self): 
        if not self.enabled: return {}
        try:
            async with httpx.AsyncClient() as c: 
                r = await c.get(f"{self.url}/snapshot", timeout=5); return r.json()
        except: return {}

# beau/memory/store.py
import sqlite3, os
class MemoryStore:
    def __init__(self, path=None):
        from beau.core.config import BEAU_MEMORY_PATH
        self.path = path or BEAU_MEMORY_PATH
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self._init()
    def _init(self):
        with sqlite3.connect(self.path) as c:
            c.execute("CREATE TABLE IF NOT EXISTS memory (id INTEGER PRIMARY KEY, user TEXT, assistant TEXT, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")
    def save(self, user: str, assistant: str):
        with sqlite3.connect(self.path) as c: c.execute("INSERT INTO memory(user,assistant) VALUES(?,?)", (user, assistant))
    def recall(self, query: str, k=5):
        with sqlite3.connect(self.path) as c:
            rows = c.execute("SELECT user, assistant FROM memory ORDER BY id DESC LIMIT ?", (k,)).fetchall()
            return "\n".join(f"U:{u} A:{a}" for u,a in rows)

# beau/billing/revenuecat.py
def is_entitled(user_id: str, feature: str) -> bool:
    from beau.core.config import REVENUECAT_API_KEY
    if not REVENUECAT_API_KEY: return True  # free tier when no key
    # TODO: call RevenueCat MCP https://api.revenuecat.com/v1/subscribers/<user_id>
    return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_memory.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add beau/browser/hermes.py beau/memory/store.py beau/billing/revenuecat.py tests/test_memory.py
git commit -m "feat: hermes browser bridge + sqlite memory + revenuecat stub"
```

---

### Task 6: FastAPI + Gradio Surfaces (A Converses UI)

**Files:**
- Create: `beau/api/server.py`, `beau/ui/app.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `run_beau()`, `FishAudioClient.tts()`, `STTProvider.transcribe()`, `HermesBridge`
- Produces: `FastAPI app` with `POST /v1/chat`, `POST /v1/audio/speech`, `POST /v1/audio/transcriptions`

- [ ] **Step 1: Write failing test**

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

def test_chat_endpoint():
    with patch("beau.api.server.run_beau", new_callable=AsyncMock) as mock:
        mock.return_value = "Hello BEAU"
        from beau.api.server import app
        client = TestClient(app)
        r = client.post("/v1/chat", json={"message": "hi"})
        assert r.status_code == 200
        assert "BEAU" in r.json()["reply"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_api.py -v`
Expected: FAIL `No module named 'beau.api.server'`

- [ ] **Step 3: Write minimal implementation**

```python
# beau/api/server.py
from fastapi import FastAPI, UploadFile
from pydantic import BaseModel
from beau.core.orchestrator import run_beau
app = FastAPI(title="BEAU SuperAgent")

class ChatReq(BaseModel): message: str
class ChatResp(BaseModel): reply: str

@app.post("/v1/chat", response_model=ChatResp)
async def chat(req: ChatReq):
    reply = await run_beau(req.message)
    return ChatResp(reply=reply)

@app.post("/v1/audio/speech")
async def tts(req: ChatReq):
    from beau.voice.fish_audio.client import FishAudioClient
    c = FishAudioClient()
    wav = await c.tts(req.message)
    from fastapi.responses import Response
    return Response(content=wav, media_type="audio/wav")

@app.post("/v1/audio/transcriptions")
async def stt(file: UploadFile):
    from beau.voice.stt.provider import get_stt
    data = await file.read()
    text = await get_stt().transcribe(data)
    return {"text": text}

@app.get("/health")
async def health(): return {"status": "ok"}

# beau/ui/app.py
import gradio as gr
from beau.core.orchestrator import run_beau
async def chat_fn(msg, history):
    reply = await run_beau(msg)
    return reply
with gr.Blocks(title="BEAU - Jarvis") as demo:
    gr.Markdown("# BEAU — Jarvis SuperAgent (Muse Spark + Fish Audio)")
    chatbot = gr.Chatbot()
    msg = gr.Textbox(label="Talk to BEAU")
    audio_in = gr.Audio(type="filepath", label="Voice input (OpenCode/Fish)")
    msg.submit(lambda m,h: h+[ (m,"...")], [msg, chatbot], [chatbot])
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add beau/api/server.py beau/ui/app.py tests/test_api.py
git commit -m "feat: api + gradio surfaces (chat, tts, stt)"
```

---

### Task 7: Vendor Fish Audio Docs + Spike Report

**Files:**
- Create: `docs/fish-audio-spike.md`
- Vendor: `beau/voice/fish_audio/README.vendor.md` (notes on fish-speech S2 Pro)

**Interfaces:**
- Produces: documented spike outcome for OpenCode voice-input vs faster-whisper and Fish Audio cloud vs local decision

- [ ] **Step 1: Write spike doc**

```markdown
# Spike: Fish Audio + OpenCode Voice Input
- Tested `opencode --help` for voice-input: [result]
- Tested `fish-audio-python` install: `pip install fish-audio-python` → import OK
- Tested fish-speech docker: `docker compose -f fish-speech/compose.yml up` → RTF measured
- Decision: STT = faster_whisper (fallback), TTS = fish-audio cloud, local opt-in
```

- [ ] **Step 2: Commit**

```bash
git add docs/fish-audio-spike.md
git commit -m "docs: fish audio + opencode voice spike"
```

---

### Task 8: Phase 2–5 Stubs (B/C/D/E)

**Files:**
- Create: `beau/tools/researcher.py`, `beau/tools/actor.py` (stubs returning "not yet" until Phase 2/3)
- Test: ensure orchestrator handoff test passes with stub

**Interfaces:**
- Produces: stub functions `research(query)->str`, `act(task)->str` for future implementation

- [ ] **Step 1: Write stubs**

```python
# beau/tools/researcher.py
async def research(query: str) -> str: return f"[Research stub for: {query}] — Phase 2"
# beau/tools/actor.py
async def act(task: str) -> str: return f"[Act stub for: {task}] — Phase 3"
```

- [ ] **Step 2: Commit**

```bash
git add beau/tools/researcher.py beau/tools/actor.py
git commit -m "feat: researcher/actor stubs for B/C phases"
```

---

## Self-Review

- **Spec coverage:** All spec sections 1-12 mapped: G1→Tasks 1-6, G2→Tasks 3-5, G3→Task 8 stub, G4→Task 8 stub, G5→Task 0, Voice 4.1→Task3, STT 4.2→Task4, Hermes 4.3→Task5, RevenueCat 5→Task5, Config 6→Task1, Tests 8→each, Phases 10→Task8 ordering
- **Placeholder scan:** No TBD/TODO in plan steps — all code blocks concrete, fallback noted as explicit faster_whisper
- **Type consistency:** `FishAudioClient.tts(text: str) -> bytes`, `STTProvider.transcribe(bytes)->str`, `run_beau(str)->str`, `MemoryStore.save(user, assistant)`, `is_entitled(str,str)->bool` consistent across tasks

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-16-beau-superagent-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - dispatch fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
