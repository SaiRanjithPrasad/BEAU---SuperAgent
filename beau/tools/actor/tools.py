import os, subprocess, tempfile
from langchain_core.tools import tool
from beau.tools.actor.models import EvaluatorOutput

SANDBOX_DEFAULT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sandbox"))
_SANDBOX = SANDBOX_DEFAULT

def _needs_confirm(cmd: str) -> bool:
    bad = ["rm -rf", "sudo", "git push --force", "rm -rf /"]
    return any(b in cmd for b in bad)

def _resolve(path: str) -> str:
    if os.path.isabs(path):
        return os.path.abspath(path)
    return os.path.abspath(os.path.join(_SANDBOX, path))

def _is_within_sandbox(path: str) -> bool:
    try:
        return os.path.commonpath([os.path.abspath(_SANDBOX), _resolve(path)]) == os.path.abspath(_SANDBOX)
    except ValueError:
        return False

@tool
def write_file(path: str, content: str) -> str:
    """Write content to path inside sandbox."""
    if not _is_within_sandbox(path):
        return f"error: path traversal blocked: {path} not inside sandbox {_SANDBOX}"
    target = _resolve(path)
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    with open(target, "w") as f: f.write(content)
    return f"Wrote {len(content)} chars to {target}"

@tool
def read_file(path: str) -> str:
    """Read file from sandbox."""
    if not _is_within_sandbox(path):
        return f"error: path traversal blocked: {path} not inside sandbox {_SANDBOX}"
    target = _resolve(path)
    with open(target) as f: return f.read()

@tool
def list_files(dir: str = ".") -> str:
    """List files in dir."""
    if not _is_within_sandbox(dir):
        return f"error: path traversal blocked: {dir} not inside sandbox {_SANDBOX}"
    target = _resolve(dir)
    return "\n".join(os.listdir(target))

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
    """Search web via Tavily. Returns mock if no key."""
    from beau.core.config import TAVILY_API_KEY
    if not TAVILY_API_KEY:
        return f"web_search stub (no TAVILY_API_KEY): {query}"
    try:
        import httpx
        resp = httpx.post(
            "https://api.tavily.com/search",
            json={"api_key": TAVILY_API_KEY, "query": query, "max_results": 5, "search_depth": "basic"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if results:
            lines = []
            for r in results[:3]:
                title = r.get("title", "")
                content = r.get("content", "")[:500]
                url = r.get("url", "")
                lines.append(f"{title}: {content} ({url})")
            return "\n".join(lines)
        return str(data)[:2000]
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
    global _SANDBOX
    _SANDBOX = os.path.abspath(sandbox)
    os.makedirs(sandbox, exist_ok=True)
    # return langchain tools + empty sessions list for compat with sidekick.py
    return [write_file, read_file, list_files, run_python, run_bash, web_search, send_email], []
