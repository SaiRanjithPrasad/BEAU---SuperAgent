# Spike: Fish Audio + OpenCode Voice Input

**Date:** 2026-09-16  
**Env:** Darwin 25.6.0 arm64, Python 3.12.12, uv 0.12.8, opencode 1.18.31, fish-audio-sdk 1.3.0, faster-whisper 1.2.1

## Tested `opencode --help` for voice-input: NOT FOUND

```bash
$ opencode --help 2>&1 | head -n 40
# → shows commands: completion, acp, mcp, attach, run, debug, providers, agent,
#   upgrade, uninstall, serve, web, models, stats, export, import, github, pr, session, plugin, db
# → no --voice, --voice-input, --audio flag in Options
$ opencode --help 2>&1 | grep -i -E "voice|audio|input|whisper|speech" || echo "no match"
no match  # exit 1
$ opencode --version
1.18.31
$ which opencode
/Users/sairanjith/.opencode/bin/opencode
```

**Result:** `opencode` (SSTA) CLI has no `voice-input` / `voice` / `audio` subcommand or flag in `1.18.31`. No STT provider via CLI available. `beau/voice/stt/provider.py:31` `OpenCodeVoiceSTT` correctly keeps faster-whisper fallback (`OpenCodeVoiceSTT.transcribe → FasterWhisperSTT.transcribe`) until/if upstream adds voice-input. Decision: do not depend on `opencode --voice-input`; keep `STT_PROVIDER=faster_whisper` default (`beau/core/config.py:16`), `opencode_voice` as opt-in stub via `get_stt("opencode_voice")`.

## Tested `fish-audio-python` install: distribution is `fish-audio-sdk` → import OK

```bash
$ uv run python -c "import importlib.metadata; print(importlib.metadata.version('fish-audio-python'))"
PackageNotFoundError: No package metadata was found for fish-audio-python

$ uv pip show fish-audio-sdk
Name: fish-audio-sdk
Version: 1.3.0
Location: /Users/sairanjith/projects/BEAU/.venv/lib/python3.12/site-packages
Requires: httpx, httpx-ws, ormsgpack, pydantic, typing-extensions

$ uv run python -c "import fish_audio_sdk; print(fish_audio_sdk.__file__)"
/Users/sairanjith/projects/BEAU/.venv/lib/python3.12/site-packages/fish_audio_sdk/__init__.py

$ uv run python -c "import fish_audio_sdk; print(dir(fish_audio_sdk))"
['APICreditEntity','ASRRequest','AsyncWebSocketSession','CloseEvent','HttpCodeErr',
 'ModelEntity','PaginatedResponse','Prosody','ReferenceAudio','Session','StartEvent',
 'TTSRequest','TextEvent','WebSocketErr','WebSocketSession', ...]

$ uv run python -c "from fish_audio_sdk import Session; s=Session('dummy'); print(type(s.tts))"
<class 'fish_audio_sdk.io.StreamIOCall'>  # has .awaitable and .this / sync generator

$ uv run python -c "from fish_audio_sdk.schemas import TTSRequest; help(TTSRequest)"
TTSRequest(text: str, chunk_length: int=200, format: Literal['wav','pcm','mp3']='mp3',
  reference_id: str|None=None, references: list[ReferenceAudio]=[], normalize=True,
  latency: Literal['normal','balanced']='balanced', ...)

$ uv run python -c "from faster_whisper import WhisperModel; print(WhisperModel)"
<class 'faster_whisper.transcribe.WhisperModel'>  # 1.2.1, import OK without model download
```

**Result:** PyPI package `fish-audio-python` does not exist (GitHub repo `fishaudio/fish-audio-python` publishes as `fish-audio-sdk`). `pyproject.toml:14` already pins `fish-audio-sdk>=1.0` (fixed Task 0 `fef42ed`). Install via `uv sync` → `fish-audio-sdk 1.3.0` → `import fish_audio_sdk` OK, `Session(apikey, base_url="https://api.fish.audio")` + `TTSRequest(text=..., reference_id=...)` + `Session.tts` (`StreamIOCall` with `awaitable` streaming + sync fallback) verified. `beau/voice/fish_audio/client.py:9` `from fish_audio_sdk import Session` + `TTSRequest(text=text, reference_id=vid)` matches SDK. Cloud TTS path requires `FISH_AUDIO_API_KEY`; `FISH_AUDIO_BASE_URL=https://api.fish.audio` default (`beau/core/config.py:13`).

## Tested fish-speech docker: Docker not available on this host → not measured; local opt-in documented

```bash
$ docker --version || docker compose version || docker-compose version
zsh: command not found: docker   # no docker on Darwin host

$ ls fish-speech 2>&1
ls: fish-speech: No such file or directory

$ cat docker-compose.yml 2>&1
cat: docker-compose.yml: No such file or directory  # no compose file vendored yet
```

**Result:** `docker` not installed on spike host, `fish-speech` repo not cloned, no `fish-speech/compose.yml` to run (`docker compose -f fish-speech/compose.yml up`). Real-time factor (RTF) therefore **not measured** on this host. Code path for local is already implemented as opt-in: `beau/voice/fish_audio/client.py:35` `if self.use_local: httpx POST {base_url}/v1/tts {"text": text, "voice": vid}` → SGLang server expected at `FISH_AUDIO_BASE_URL` when `FISH_AUDIO_USE_LOCAL=true` (`beau/core/config.py:12`). This matches Task 3 design (cloud default, local opt-in). For local S2 Pro, vendor notes would go in `beau/voice/fish_audio/README.vendor.md` (fish-speech S2 Pro, SGLang, Docker GPU, RTF target <0.3 on A100 / <1.0 on 4090 per upstream) — not required for this spike (brief § Step 1 doc-only), see Decision below.

Note: speculative local vendor doc deferred per instruction “Brief says just doc file, no code” — no `beau/voice/fish_audio/README.vendor.md` created in this task; create in Tasks 3/8 hardening if local bench is run on GPU host.

## Decision

- **STT = faster_whisper (fallback)** — `STT_PROVIDER=faster_whisper` default; `FasterWhisperSTT` (`beau/voice/stt/provider.py:13`) uses `faster-whisper 1.2.1` `WhisperModel("base", device="cpu", compute_type="int8")` + temp wav file. `OpenCodeVoiceSTT` (`provider.py:31`) stays as fallback-delegating stub until `opencode --help` gains voice-input; `get_stt("opencode_voice")` routes there when `STT_PROVIDER=opencode_voice` (env opt-in). No dependency on missing `opencode voice-input`.

- **TTS = fish-audio cloud (default), local opt-in** — Cloud via `fish-audio-sdk 1.3.0` `Session(api_key, base_url="https://api.fish.audio")` + `TTSRequest(text, reference_id=voice_id)` (tags like `[whisper]` passthrough). Local S2 Pro (`fish-speech` SGLang Docker) via `FISH_AUDIO_USE_LOCAL=true` + `FISH_AUDIO_BASE_URL=http://localhost:8000` (example) → `httpx POST /v1/tts`. Env defaults in `beau/core/config.py:11-14` (`FISH_AUDIO_API_KEY=""`, `FISH_AUDIO_USE_LOCAL=false`, `FISH_AUDIO_BASE_URL="https://api.fish.audio"`, `FISH_AUDIO_VOICE_ID="beau_jarvis"`).

- **OpenCode voice-input:** not available in `1.18.31`; re-spike if `opencode --help` later shows `voice`/`audio` flag (check `opencode models` + `opencode providers` as well). Until then, `opencode_voice` STT is mockable stub; production STT stays `faster_whisper`.

## Repro

```bash
opencode --help 2>&1 | grep -i voice; echo $?
opencode --version
uv run python -c "import fish_audio_sdk; print(fish_audio_sdk.__file__)"
uv run python -c "import importlib.metadata; print(importlib.metadata.version('fish-audio-sdk'))"
uv run python -c "from faster_whisper import WhisperModel; print('ok')"
docker --version 2>&1 || echo "no docker"
```
