"""
Central OpenRouter configuration shim — re-export from beau.core.config.

Canonical config lives in beau.core.config; this module exists for backward
compat (imports like `import openrouter_config`). Do not duplicate os.getenv
logic here; read from beau.core.config at call time.
"""
import beau.core.config as _cfg

# Re-export canonical values (evaluated at import time for compatibility)
OPENROUTER_API_KEY = _cfg.OPENROUTER_API_KEY
OPENROUTER_BASE_URL = _cfg.OPENROUTER_BASE_URL
OPENROUTER_MODEL = _cfg.OPENROUTER_MODEL
DEFAULT_MODEL_NAME = _cfg.DEFAULT_MODEL_NAME

# Also re-export helpers that mirror to OpenAI env
load_config = _cfg.load_config


def get_openai_client():
    """Return an OpenAI client pointed at OpenRouter if key exists, else default."""
    from openai import OpenAI

    # Read current values from canonical config
    if _cfg.OPENROUTER_API_KEY:
        return OpenAI(api_key=_cfg.OPENROUTER_API_KEY, base_url=_cfg.OPENROUTER_BASE_URL)
    return OpenAI()


def get_chat_openai(**kwargs):
    """Return ChatOpenAI pointed at OpenRouter."""
    from langchain_openai import ChatOpenAI

    model = kwargs.pop("model", _cfg.OPENROUTER_MODEL)
    api_key = kwargs.pop("api_key", _cfg.OPENROUTER_API_KEY)
    base_url = kwargs.pop("base_url", _cfg.OPENROUTER_BASE_URL)
    return ChatOpenAI(model=model, api_key=api_key, base_url=base_url, **kwargs)


def get_agent_model():
    """Return model string for Agents SDK."""
    return _cfg.OPENROUTER_MODEL
