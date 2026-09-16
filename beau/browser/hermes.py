import logging
import httpx
from beau.core.config import HERMES_BROWSER_MCP_URL, HERMES_ENABLED

logger = logging.getLogger(__name__)


class HermesBridge:
    def __init__(self, url=HERMES_BROWSER_MCP_URL, enabled=HERMES_ENABLED):
        self.url = url; self.enabled = enabled
    async def play_audio(self, wav: bytes):
        if not self.enabled: return
        try:
            async with httpx.AsyncClient() as c: await c.post(f"{self.url}/play", content=wav, timeout=5)
        except Exception:
            logger.warning("HERMES_UNAVAILABLE")
            return
    async def snapshot(self):
        if not self.enabled: return {}
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(f"{self.url}/snapshot", timeout=5); return r.json()
        except Exception:
            logger.warning("HERMES_UNAVAILABLE")
            return {}
