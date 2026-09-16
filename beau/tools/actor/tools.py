import os, subprocess, tempfile
from langchain_core.tools import tool
from beau.tools.actor.models import EvaluatorOutput

def _needs_confirm(cmd: str) -> bool:
    bad = ["rm -rf", "sudo", "git push --force", "rm -rf /"]
    return any(b in cmd for b in bad)

@tool
def write_file(path: str, content: str) -> str:
    """Write content to path inside sandbox."""
    # caller ensures path is inside sandbox
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f: f.write(content)
    return f"Wrote {len(content)} chars to {path}"

@tool
def read_file(path: str) -> str:
    """Read file from sandbox."""
    with open(path) as f: return f.read()

@tool
def list_files(dir: str = ".") -> str:
    """List files in dir."""
    return "\n".join(os.listdir(dir))

@tool
def run_python(code: str) -> str:
    """Run python code in sandbox."""
    result = subprocess.run(["python3", "-c", code], capture_output=True, text=True, timeout=10)
    return result.stdout + result.stderr

@tool
def run_bash(command: str) -> str:
    """Run bash command. Returns needs_confirm flag for destructive commands."""
    if _needs_confirm(command):
        return f"needs_confirm:true command:{command}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
    return result.stdout + result.stderr

@tool
def web_search(query: str) -> str:
    """Search web via Tavily stub. Returns mock if no key."""
    from beau.core.config import TAVILY_API_KEY
    if not TAVILY_API_KEY:
        return f"web_search stub (no TAVILY_API_KEY): {query}"
    # lazy import to avoid hard dep if missing
    try:
        import httpx
        return f"web_search result for: {query} (TAVILY_API_KEY set)"
    except Exception as e:
        return f"web_search error: {e}"

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send email stub. Respects USE_EMAIL flag."""
    from beau.core.config import USE_EMAIL
    if not USE_EMAIL:
        return f"send_email disabled (USE_EMAIL=false): to={to} subject={subject}"
    return f"Email sent to {to}: {subject}"

async def get_all_tools(sandbox: str):
    # ensure sandbox exists
    os.makedirs(sandbox, exist_ok=True)
    # return langchain tools + empty sessions list for compat with sidekick.py
    return [write_file, read_file, list_files, run_python, run_bash, web_search, send_email], []
