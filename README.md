# BEAU SuperAgent

> Jarvis-like personal Super Agent — voice-first, browser-connected, persistent.

**Priority:** A > B > C > D > E — Converses > Researches > Acts > Automates > Orchestrates  
**LLM:** Muse Spark (`meta/muse-spark-1.2-contributor`) via OpenRouter — see `openrouter_config.py`  
**Voice:** Fish Audio S2 Pro (Dual-AR 4B, 80+ langs, 32.7k★) + Hermes Agent browser bridge + OpenCode voice-input spike  
**Billing:** RevenueCat MCP (stub v1)  
**Repo:** https://github.com/SaiRanjithPrasad/BEAU---SuperAgent

## Quick Start

```bash
cp .env.example .env  # add OPENROUTER_API_KEY=sk-or-v1-..., FISH_AUDIO_API_KEY=...
uv sync
uv run python test_openrouter_muse_spark.py  # validates Muse Spark via OpenRouter
uv run python -m beau.ui.app  # Gradio Jarvis UI
```

## Docs

- Spec: `docs/superpowers/specs/2026-09-16-beau-superagent-design.md`
- Plan: `docs/superpowers/plans/` (after `writing-plans` skill)

## Architecture

See spec Section 3 — Modular Master+Workers (Orchestrator → Researcher/Actor + Fish Audio voice + Hermes browser).

## Validation

- OmniRoute: `omniroute providers test openrouter` → OK (957b9614)
- Fish Audio: `fish-speech` S2 Pro RTF 0.195, TTFA ~100ms (H200)
