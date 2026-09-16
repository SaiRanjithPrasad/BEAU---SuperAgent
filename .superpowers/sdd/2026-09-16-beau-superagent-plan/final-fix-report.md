# Final Fix Report — 719c72a findings (5 Important)

**Base:** 719c72a  
**Date:** 2026-09-16  
**Diff reviewed:** eb1b383..719c72a

## Findings fixed

1. **Gradio UI never calls orchestrator** `beau/ui/app.py:2-11`
   - Before: `msg.submit(lambda m,h: h+[(m,"...")], ...)` placeholder, `audio_in` unused, no `queue()`.
   - Fix: `chat_fn(msg, history)` returns `history+[(msg, reply)]`; `msg.submit(chat_fn, [msg, chatbot], [chatbot])`; `audio_in.change(audio_fn, [audio_in, chatbot], [chatbot])` where `audio_fn` reads file, `get_stt().transcribe`, `run_beau`, optional `FishAudioClient.tts` + `HermesBridge.play_audio` (best-effort); added `demo.queue()`. `beau/ui/app.py:1-42`

2. **STT tempfile leak** `beau/voice/stt/provider.py:21-26`
   - Before: `NamedTemporaryFile(delete=False)` + `os.unlink` only on success; exception leaks file.
   - Fix: `path=None` init, `try: write+transcribe+return` `except: return "[STT error: {e}]"` `finally: if path: try: os.unlink except FileNotFoundError/pass`. `beau/voice/stt/provider.py:13-33`

3. **Config divergence — openrouter_config.py not shim** `beau/core/config.py:1-34 vs openrouter_config.py:1-55`
   - Before: duplicated `os.getenv` block diverging from canonical config.
   - Fix: `openrouter_config.py` now `import beau.core.config as _cfg` and re-exports `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`, `DEFAULT_MODEL_NAME`, `load_config`; `get_openai_client/get_chat_openai/get_agent_model` read `_cfg.*` at call time. Removed duplicated `load_dotenv/os.getenv` block. `openrouter_config.py:1-39`

4. **Missing failure modes** — `beau/voice/fish_audio/client.py` 429, `beau/browser/hermes.py` bare except, `beau/billing/revenuecat.py`
   - FishAudio: added `logging` + `httpx.HTTPStatusError` 429 handling; local path logs `FISH_AUDIO_429` and re-raises; cloud path catches 429, logs `FISH_AUDIO_429`, if `use_local` retries local POST else re-raises. `beau/voice/fish_audio/client.py:1-7,36-49,64-178`
   - Hermes: added `logging.warning("HERMES_UNAVAILABLE")` in both `play_audio` and `snapshot` except blocks, removed bare `except: pass`. `beau/browser/hermes.py:1-21`
   - Billing: added `logging.warning("BILLING_UNAVAILABLE")` when `REVENUECAT_API_KEY` set but not implemented. `beau/billing/revenuecat.py:1-11`

5. **MemoryStore.recall ignores query** `beau/memory/store.py:13-16`
   - Before: `ORDER BY id DESC LIMIT ?` ignores `query`.
   - Fix: `if query: SELECT ... WHERE user LIKE ? OR assistant LIKE ?` with `%query%` fallback to recent if no LIKE rows; `else: ORDER BY id DESC`. Keeps backward compat when `query==""`. `beau/memory/store.py:10-20`

## Extras per task

- `beau/sandbox/.gitkeep` and `data/.gitkeep` added (force-added, `data/` is gitignored). Plan File Structure compliance.
- `.env.example` STT_PROVIDER aligned to `faster_whisper` with comment: faster_whisper default, opencode_voice opt-in stub. `.env.example:15-17`
- Removed unused `import os` in `beau/core/orchestrator.py:1`.

## Tests

```
$ uv run pytest tests/ -v
13 passed (test_api, test_config x2, test_fish_audio x2, test_memory, test_orchestrator x2, test_scaffold x3, test_stt x2)
```

Manual checks:
- `import beau.ui.app; demo.queue` OK
- `openrouter_config.OPENROUTER_MODEL == beau.core.config.OPENROUTER_MODEL` true
- `MemoryStore.recall("hello")` filters correctly, `recall("")` returns recent, missing query falls back to recent
- `is_entitled` logs BILLING_UNAVAILABLE when key set

## Commits

Single fix commit on top of 719c72a covering all 5 findings + extras.
