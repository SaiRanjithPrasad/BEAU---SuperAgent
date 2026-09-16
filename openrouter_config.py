"""
Central OpenRouter configuration for Muse Spark migration.

Set in .env:
  OPENROUTER_API_KEY=sk-or-v1-...
  OPENROUTER_BASE_URL=https://openrouter.ai/api/v1  (optional)
  OPENROUTER_MODEL=meta/muse-spark-1.2-contributor  (optional)

This module:
  - loads .env
  - mirrors OPENROUTER creds to OPENAI_* for Agents SDK compatibility
  - exposes helpers for OpenAI client, ChatOpenAI, and Agents
"""
import os
from dotenv import load_dotenv

load_dotenv(override=True)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta/muse-spark-1.2-contributor")
# Also support OPENROUTER_MODEL env as WORKER_MODEL / DEFAULT_MODEL_NAME fallbacks
# For backward compat, also check OPENROUTER_MODEL via WORKER_MODEL
if not os.getenv("OPENROUTER_MODEL") and os.getenv("WORKER_MODEL"):
    OPENROUTER_MODEL = os.getenv("WORKER_MODEL")

# Mirror to OpenAI env vars so `agents` SDK (which reads OPENAI_API_KEY/BASE_URL) works with OpenRouter
if OPENROUTER_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENROUTER_API_KEY
    os.environ["OPENAI_BASE_URL"] = OPENROUTER_BASE_URL

# For libraries that read these directly
DEFAULT_MODEL_NAME = OPENROUTER_MODEL

def get_openai_client():
    """Return an OpenAI client pointed at OpenRouter if key exists, else default."""
    from openai import OpenAI
    if OPENROUTER_API_KEY:
        return OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
    # fallback to default (will use OPENAI_API_KEY from env if present)
    return OpenAI()

def get_chat_openai(**kwargs):
    """Return ChatOpenAI pointed at OpenRouter."""
    from langchain_openai import ChatOpenAI
    # allow override
    model = kwargs.pop("model", OPENROUTER_MODEL)
    api_key = kwargs.pop("api_key", OPENROUTER_API_KEY)
    base_url = kwargs.pop("base_url", OPENROUTER_BASE_URL)
    # langchain-openai supports both `api_key`/`base_url` and `openai_api_key`/`openai_api_base`
    return ChatOpenAI(model=model, api_key=api_key, base_url=base_url, **kwargs)

def get_agent_model():
    """Return model string for Agents SDK."""
    return OPENROUTER_MODEL
