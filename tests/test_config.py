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
