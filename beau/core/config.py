import os
from dotenv import load_dotenv
# override=False so process env (tests, CI, Docker) wins over .env file —
# override=True would let .env clobber monkeypatched/test env vars.
load_dotenv(override=False)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", os.getenv("DEFAULT_MODEL_NAME", "meta/muse-spark-1.2-contributor"))
if not os.getenv("OPENROUTER_MODEL") and os.getenv("WORKER_MODEL"):
    OPENROUTER_MODEL = os.getenv("WORKER_MODEL")

FISH_AUDIO_API_KEY = os.getenv("FISH_AUDIO_API_KEY", "")
FISH_AUDIO_USE_LOCAL = os.getenv("FISH_AUDIO_USE_LOCAL", "false").lower() == "true"
FISH_AUDIO_BASE_URL = os.getenv("FISH_AUDIO_BASE_URL", "https://api.fish.audio")
FISH_AUDIO_VOICE_ID = os.getenv("FISH_AUDIO_VOICE_ID", "beau_jarvis")

TTS_PROVIDER = os.getenv("TTS_PROVIDER", "auto")  # auto | fish_audio | edge | piper
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "en-US-JennyNeural")

# Piper — offline TTS fallback (voice models in PIPER_VOICE_DIR)
PIPER_VOICE_DIR = os.getenv("PIPER_VOICE_DIR", "./data/piper-voices")
PIPER_VOICE = os.getenv("PIPER_VOICE", "en_US-lessac-medium")

STT_PROVIDER = os.getenv("STT_PROVIDER", "faster_whisper")
HERMES_ENABLED = os.getenv("HERMES_ENABLED", "true").lower() == "true"
HERMES_BROWSER_MCP_URL = os.getenv("HERMES_BROWSER_MCP_URL", "http://localhost:3000/mcp")

REVENUECAT_API_KEY = os.getenv("REVENUECAT_API_KEY", "")
REVENUECAT_ENTITLEMENT = os.getenv("REVENUECAT_ENTITLEMENT", "beau_pro")
BEAU_MEMORY_PATH = os.getenv("BEAU_MEMORY_PATH", "./data/beau.db")
BEAU_API_PORT = int(os.getenv("BEAU_API_PORT", "7860"))

HOW_MANY_SEARCHES = int(os.getenv("HOW_MANY_SEARCHES", 3))

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
USE_EMAIL = os.getenv("USE_EMAIL", "false").lower() == "true"

DEFAULT_MODEL_NAME = OPENROUTER_MODEL

def load_config():
    if OPENROUTER_API_KEY:
        os.environ["OPENAI_API_KEY"] = OPENROUTER_API_KEY
        os.environ["OPENAI_BASE_URL"] = OPENROUTER_BASE_URL
    return {
        "OPENROUTER_MODEL": OPENROUTER_MODEL,
        "FISH_AUDIO_USE_LOCAL": FISH_AUDIO_USE_LOCAL,
    }
