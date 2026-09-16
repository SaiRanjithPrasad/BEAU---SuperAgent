# BEAU SuperAgent — Design Spec

**Date:** 2026-09-16  
**Repo:** https://github.com/SaiRanjithPrasad/BEAU---SuperAgent  
**Status:** Draft → Awaiting review before `writing-plans`  
**Author:** SaiRanjithPrasad + Muse Spark (via brainstorming skill)  
**Parent migration:** `/Users/sairanjith/projects/agents` staged Super Agent session (`openrouter_config.py:1`, `test_openrouter_muse_spark.py:1`, `.env:3` `sk-or-v1-...`, 36 files staged for `meta/muse-spark-1.2-contributor` via OpenRouter)

---

## 1. Summary

BEAU is a **Jarvis-like personal Super Agent** — voice-first, browser-connected, persistent — prioritizing **A>B>C>D>E**: Converses > Researches > Acts > Automates > Orchestrates. Orchestrator is **Muse Spark (`meta/muse-spark-1.2-contributor`) via OpenRouter (`openrouter_config.py:20` https://openrouter.ai/api/v1)** with mirroring to `OPENAI_*` for Agents SDK compatibility. Voice uses **Fish Audio S2 Pro (Dual-AR 4B, 80+ langs, RTF 0.195, TTFA ~100ms, 32.7k stars)** for TTS + **Hermes Agent** for browser-native voice interaction + **OpenCode voice-input** spike (vs typing) for STT. Monetization via **RevenueCat MCP**. This spec stages incrementally so `A` ships first.

---

## 2. Goals / Non-Goals

**Goals v1 (MVP):**
- G1: Natural conversation with Jarvis persona, persistent memory, latency <1.5s end-to-end (Muse Spark + Fish Audio streaming).
- G2: Voice in/out without typing: Hermes Agent browser bridge + Fish Audio TTS (cloud `fish-audio-python` first, local `fish-speech` Docker/SGLang fallback), STT via OpenCode voice-input spike vs Whisper fallback.
- G3: Research capability reusing `2_openai/deep_research` (planner/search/writer) for web synthesis.
- G4: Action capability reusing `4_langchain_langgraph/sidekick.py:100` sandboxed tools + `6_mcp/backend/trading_floor.py:1` tool pattern.
- G5: Repo scaffolding + spec-driven delivery in `BEAU` with clean git history.

**Non-Goals v1:**
- Full multi-agent orchestration (CrewAI/LangGraph/MCP orchestration) — deferred to post-MVP (`E`).
- Voice cloning at scale beyond 1–2 reference voices (10–30s sample).
- RevenueCat paywall enforcement v1 — only MCP plumbing + entitlement check stub.
- Mobile app — web/CLI only.

**Success criteria:**
- `uv run python test_openrouter_muse_spark.py` passes 3/3 (OpenAI client, LangChain, Agents SDK) with `OPENROUTER_MODEL=meta/muse-spark-1.2-contributor`.
- `curl http://localhost:20128/v1/chat/completions -d '{"model":"openrouter/openai/gpt-4o-mini"}'` validated; same pattern works for `openrouter/meta/muse-spark-1.2-contributor` via OmniRoute.
- Voice loop: speak → STT → BEAU → Fish Audio TTS → playback <2s, browser Hermes Agent reflects state.
- `omniroute providers test openrouter` OK, Gradio at `http://localhost:7860` shows BEAU chat.

---

## 3. Architecture

### 3.1 High-Level

```
User ─┬─ Browser (Gradio + Hermes Agent extension/MCP) ─┬─ FastAPI /v1/*
      ├─ Voice Input (OpenCode voice-input || Whisper STT) ─┤
      └─ CLI ───────────────────────────────────────────┤
                                                      │
                                          ┌───────────▼───────────┐
                                          │  BEAU Orchestrator    │
                                          │  Muse Spark via       │
                                          │  openrouter_config    │
                                          │  (mirrors OPENAI_*)   │
                                          └───────────┬───────────┘
                                                      │ handoffs
                    ┌─────────────────┬─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼                 ▼
              Researcher          Actor            Scheduler         Evaluator
           (deep_research)    (sidekick tools)   (agent_loop)    (structured)
                    │                 │                 │
                    └─────────────────┼─────────────────┘
                                      ▼
                              Tool/MCP Layer
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
                Fish Audio       RevenueCat        Web/Search
              (fish-speech S2)     MCP            (Tavily)
              fish-audio-python
                    │
                    ▼
              Memory (SQLite)
              beau/memory/
```

**Source reuse:** Directly ports staged `agents` migration: `openrouter_config.py:28` mirroring, `1_foundations/twin/app.py:8` OpenRouter client pattern, `sidekick.py:104` ChatOpenAI with `api_key/base_url`.

### 3.2 Components

| Component | Path | Responsibility | Interface |
|-----------|------|----------------|-----------|
| **Orchestrator** | `beau/core/orchestrator.py` | Jarvis persona, routing `A>B>C`, handoffs | `Agent(name="BEAU", model=OPENROUTER_MODEL, instructions=JARVIS_PROMPT)` + `Runner.run()` |
| **Voice TTS** | `beau/voice/fish_audio/` | Fish Audio S2 Pro TTS, voice clone, streaming | `fish-audio-python` SDK (`fish.audio` API) + local `fish_speech` Docker (SGLang/vLLM-Omni). Tags: `[whisper] [excited] [pause]` via S2 inline control |
| **Voice STT** | `beau/voice/stt/` | Speech-to-text | Spike: `opencode voice-input` → if unavailable, `openai-whisper`/`faster-whisper` fallback. Abstract `STTProvider` interface |
| **Browser Bridge** | `beau/browser/hermes.py` | Hermes Agent ↔ browser (Gradio + MCP) | Hermes Agent SDK/MCP server, exposes `browser_navigate`, `browser_snapshot`, `voice_play` tools to orchestrator |
| **Researcher** | `beau/tools/researcher.py` | Web research | Ports `2_openai/deep_research/planner_agent.py:1`, `search_agent.py:1`, `writer_agent.py:1` with `OPENROUTER_MODEL` |
| **Actor** | `beau/tools/actor.py` | Sandboxed actions | Ports `4_langchain_langgraph/sidekick.py:100`, `get_all_tools(SANDBOX)` |
| **Memory** | `beau/memory/store.py` | Persistent recall | SQLite + `6_mcp/memory` pattern, `agents/memory` vector fallback |
| **Billing** | `beau/billing/revenuecat.py` | Entitlements | RevenueCat MCP server (proposed `mcp-revenuecat`), `is_entitled(feature)` check before voice clone/premium tools |
| **API** | `beau/api/server.py` | HTTP surface | FastAPI: `POST /v1/chat`, `POST /v1/audio/speech`, `POST /v1/audio/transcriptions`, `GET /health` |
| **UI** | `beau/ui/app.py` | Gradio Jarvis UI | Reuses `1_foundations/twin/app.py:1` Gradio pattern, adds voice waveform + browser Hermes panel |

### 3.3 Data Flow (A>B>C)

1. **A Converses:** User voice → STT (OpenCode/Whisper) → text → `orchestrator` (Muse Spark) → memory lookup → response text → Fish Audio TTS (streaming, ~100ms TTFA) → playback + browser Hermes update.
2. **B Researches:** Orchestrator detects research intent → handoff `researcher` → `planner → search (Tavily) → writer` → synthesized markdown → optional Fish Audio narration.
3. **C Acts:** Orchestrator → `actor` → tool call in `SANDBOX` (`beau/sandbox/`) → result → evaluator (`ChatOpenAI(...).with_structured_output(EvaluatorOutput)` like `sidekick.py:121`) → retry or final.

---

## 4. Voice Stack Detail

### 4.1 Fish Audio S2 Pro (from https://github.com/fishaudio)

- **What we vendor:** `fishaudio/fish-audio-python` (Apache-2.0, `fish-audio-python:1`) as primary SDK; `fishaudio/fish-speech` (`pyproject.toml:1`, `fish_speech/`, `tools/`, `docker/`, `compose.yml`) as optional local inference. Pin to `fish-speech` tag `v1.x` at plan time.
- **Why S2 Pro:** 10M hours, 80+ langs, Dual-AR (Slow 4B + Fast 400M), GRPO RL alignment, `[tag]` inline prosody (`[whisper] [excited] [pause] [laughing]` etc.), native multi-speaker via `<|speaker:i|>`, voice clone 10–30s, H200 RTF 0.195, TTFA ~100ms via SGLang.
- **Integration:** `beau/voice/fish_audio/client.py` wraps `fish-audio-python` `FishAudioClient(api_key=..., base_url="https://api.fish.audio")` and local `http://localhost:8000/v1/tts` (fish-speech SGLang server). Config: `FISH_AUDIO_API_KEY`, `FISH_AUDIO_USE_LOCAL=false`, `FISH_VOICE_ID=beau_jarvis`.
- **License check:** Fish Speech is **FISH AUDIO RESEARCH LICENSE** (not Apache/MIT) — commercial use requires review. v1 will default to cloud API (Apache-2.0 SDK) to avoid self-hosting license concerns; local is opt-in.

### 4.2 STT: OpenCode Voice-Input Spike

- **Decision:** Spike before building. Tasks:
  1. Check `opencode` CLI/docs for `voice-input` capability (search `openrouter-src/OmniRoute/skills`, `opencode.jsonc:1`, `opencode` help).
  2. If exists: test latency/accuracy vs `faster-whisper` baseline in `beau/voice/stt/`.
  3. If not: recommend `faster-whisper` (local) or `fish-audio` STT if offered, and keep OpenCode for orchestration.
- **Interface:** `STTProvider.transcribe(audio_bytes) -> text` so implementations are swappable.

### 4.3 Hermes Agent ↔ Browser

- **Role:** Built-in voice agent that *lives in browser* — provides continuous listening, barge-in, and visual reflection (what BEAU sees).
- **Implementation:** Hermes Agent MCP server + browser extension or Gradio `Audio` component with `streaming=True`. Tools exposed: `browser_navigate(url)`, `browser_snapshot()`, `play_audio(wav_bytes)`, `on_voice_activity(text)`.
- **Visual companion alignment:** Per brainstorming skill, browser companion is offered just-in-time for voice calibration (waveform, voice clone preview) — not for every question.

---

## 5. RevenueCat MCP

- **Purpose:** Gate premium features (voice clone slots, research depth, sandbox compute) behind entitlements.
- **MCP server:** Propose `mcp-revenuecat` (or `omni-provider` wrapping RevenueCat API `https://api.revenuecat.com/v1`). Config: `REVENUECAT_API_KEY`, `REVENUECAT_ENTITLEMENT=beau_pro`.
- **Flow:** Before premium tool call, `revenuecat.is_entitled(user_id, "beau_pro")` → if false, degrade gracefully (free-tier Muse Spark gratis model `muse-spark-1.2-contributor-free`, limited TTS).
- **Defer:** Full paywall UI deferred past v1; v1 only stubs check + logs.

---

## 6. Configuration

Reuses `agents/.env:1` pattern, centralized in `beau/core/config.py` (mirrors `openrouter_config.py:1`):

```env
# LLM (Muse Spark via OpenRouter)
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=meta/muse-spark-1.2-contributor
DEFAULT_MODEL_NAME=meta/muse-spark-1.2-contributor
WORKER_MODEL=meta/muse-spark-1.2-contributor

# Voice - Fish Audio
FISH_AUDIO_API_KEY=...
FISH_AUDIO_USE_LOCAL=false
FISH_AUDIO_VOICE_ID=beau_jarvis
FISH_AUDIO_BASE_URL=https://api.fish.audio

# STT
STT_PROVIDER=opencode_voice # or faster_whisper
OPENCODE_VOICE_INPUT_ENABLED=true

# Hermes Browser
HERMES_BROWSER_MCP_URL=http://localhost:3000/mcp
HERMES_ENABLED=true

# RevenueCat
REVENUECAT_API_KEY=
REVENUECAT_ENTITLEMENT=beau_pro

# Memory/API
BEAU_MEMORY_PATH=./data/beau.db
BEAU_API_PORT=7860
```

`openrouter_config.py:28` mirroring (`OPENAI_API_KEY=OPENROUTER_API_KEY`, `OPENAI_BASE_URL=OPENROUTER_BASE_URL`) retained for Agents SDK compatibility.

---

## 7. Error Handling

- **LLM fallback:** If `muse-spark-1.2-contributor` errors (rate limit), fallback to `muse-spark-1.2-contributor-free` or `openai/gpt-4o-mini` via `openrouter/openai/gpt-4o-mini` (validated in OmniRoute test).
- **TTS fallback:** If Fish Audio API 429/error → fallback to local `fish-speech` if `FISH_AUDIO_USE_LOCAL=true`, else degrade to text-only with warning. Cache last 5s of TTS for replay.
- **STT fallback:** If OpenCode voice-input unavailable → auto-switch to `faster-whisper`.
- **Hermes fallback:** If browser MCP unreachable → CLI/Gradio audio component still works; log `HERMES_UNAVAILABLE`.
- **RevenueCat fallback:** If MCP unreachable → allow free-tier, log `BILLING_UNAVAILABLE`, don't block.

---

## 8. Testing

- **Unit:** `pytest` for `beau/voice/fish_audio/client.py` (mock SDK), `beau/voice/stt/` provider interface, `beau/memory/store.py`, `beau/billing/revenuecat.py` (mock 403/200).
- **Integration:** `test_openrouter_muse_spark.py:47`-style live test extended to BEAU: `uv run python test_beau_voice.py` (STT→Orchestrator→TTS round-trip), `omniroute providers test openrouter`, Gradio smoke test.
- **Manual:** Voice latency budget: STT 300ms + LLM 700ms + TTS TTFA 100ms = ~1.1s target; measure via `beau/tools/bench.py`.

---

## 9. Repo Structure (target)

```
BEAU/
├── beau/
│   ├── core/
│   │   ├── config.py          # mirrors openrouter_config.py
│   │   ├── orchestrator.py    # BEAU Agent + Runner
│   │   └── prompts.py         # JARVIS_PROMPT
│   ├── voice/
│   │   ├── fish_audio/client.py
│   │   └── stt/provider.py
│   ├── browser/hermes.py
│   ├── tools/
│   │   ├── researcher.py
│   │   └── actor.py
│   ├── memory/store.py
│   ├── billing/revenuecat.py
│   ├── api/server.py
│   └── ui/app.py
├── docs/superpowers/specs/2026-09-16-beau-superagent-design.md (this file)
├── openrouter_config.py       # copied from agents staged session
├── test_openrouter_muse_spark.py
├── .env.example
├── pyproject.toml
├── compose.yml                # optional fish-speech SGLang
└── README.md
```

Initial `pyproject.toml` dependencies: `openai`, `agents`, `langchain-openai`, `gradio`, `fastapi`, `uvicorn`, `fish-audio-python`, `faster-whisper` (optional), `python-dotenv`.

---

## 10. Phases (aligned to A>B>C>D>E)

- **Phase 0 — Scaffold (this commit):** Init repo, `docs/superpowers/specs/`, `openrouter_config.py` + `.env.example`, `pyproject.toml`, `README`, `beau/` skeleton, `omniroute` provider `openrouter` validated.
- **Phase 1 — A Converses + Voice (v1 MVP):** Orchestrator + Hermes browser + Fish Audio TTS (cloud) + STT spike + Gradio. Ships Jarvis chat.
- **Phase 2 — B Researches:** Port `deep_research` agents.
- **Phase 3 — C Acts:** Port `sidekick` sandbox tools.
- **Phase 4 — D Automates + E Orchestrates + RevenueCat:** Scheduler, multi-agent handoffs, billing gate.
- **Phase 5 — Local Fish-Speech + Polish:** Docker `fish-speech` SGLang, voice clone UI, perf tuning.

Each phase gets own `writing-plans` plan after this spec is approved.

---

## 11. Open Questions (resolve before Phase 1 plan)

- Q1: Confirm `FISH_AUDIO_API_KEY` source (same OpenRouter key or separate fish.audio account)?
- Q2: Confirm Hermes Agent MCP endpoint/binding — use existing `Hermes Agent` skill in `~/.config/opencode/omniroute-src/OmniRoute/skills/hermes` or custom?
- Q3: RevenueCat product IDs and entitlement mapping?
- Q4: Voice clone reference audio owner/consent (use Fish Audio docs `voices`)?
- Q5: Confirm `STT_PROVIDER` final after OpenCode voice-input spike.

---

## 12. Alternatives Considered

See Section 3 proposals. Approach 2 (Modular Master+Workers) chosen for staged `A>B>C` delivery, reuse of staged `agents` migration, and Fish Audio license-safe cloud-first strategy.

---

*End of spec. Next: `writing-plans` skill to generate `docs/superpowers/plans/2026-09-16-beau-superagent-plan.md` after user approval.*
