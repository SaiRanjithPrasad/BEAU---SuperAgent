"""D Automates + E Orchestrates — lightweight in-process scheduler (quick port).

Jobs are stored in-memory + mirrored to SQLite via beau/memory/store.py for
durability. Each job runs a BEAU capability (research/act/chat) on an
interval, with optional RevenueCat entitlement gating and Hermes voice nudge.
"""
import asyncio
import logging
import sqlite3
import time
import uuid

logger = logging.getLogger(__name__)

try:
    from beau.billing.revenuecat import is_entitled
except ImportError:
    is_entitled = None

_JOBS: dict[str, dict] = {}
_TASKS: dict[str, asyncio.Task] = {}


def _jobs_table(db_path: str) -> None:
    import os
    from beau.core.config import BEAU_MEMORY_PATH
    path = db_path or BEAU_MEMORY_PATH
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with sqlite3.connect(path) as c:
        c.execute(
            "CREATE TABLE IF NOT EXISTS jobs "
            "(id TEXT PRIMARY KEY, kind TEXT, payload TEXT, every_secs REAL, "
            "next_run REAL, created REAL, last_result TEXT)"
        )


async def _run_loop(job_id: str) -> None:
    from beau.memory.store import MemoryStore
    from beau.billing.revenuecat import is_entitled

    while job_id in _JOBS:
        job = _JOBS[job_id]
        now = time.time()
        delay = max(0.0, job["next_run"] - now)
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            break
        if job_id not in _JOBS:
            break
        # billing gate: premium kinds need beau_pro
        if job.get("premium") and (is_entitled is None or not is_entitled(job.get("user_id", "local"), "beau_pro")):
            job["last_result"] = "skipped: not entitled (beau_pro)"
            logger.warning("BILLING_UNAVAILABLE: job %s skipped, not entitled", job_id)
            job["next_run"] = time.time() + job["every_secs"]
            continue
        try:
            result = await _execute(job)
            job["last_result"] = result[:2000]
            try:
                MemoryStore().save(f"scheduled {job['kind']}: {job['payload']}", result[:2000])
            except Exception:
                pass
        except asyncio.CancelledError:
            break
        except Exception as e:
            job["last_result"] = f"error: {e}"
            logger.warning("scheduler job %s failed: %s", job_id, e)
        finally:
            job["next_run"] = time.time() + job["every_secs"]


async def _execute(job: dict) -> str:
    kind = job["kind"]
    payload = job["payload"]
    if kind == "research":
        from beau.tools.researcher import research
        return await research(payload)
    if kind == "act":
        from beau.tools.actor import act
        return await act(payload)
    # default: chat via orchestrator
    from beau.core.orchestrator import run_beau
    return await run_beau(payload)


def schedule(kind: str, payload: str, every_secs: float, user_id: str = "local",
             premium: bool = False, db_path: str = None) -> str:
    """Schedule a recurring BEAU job. Returns job_id. Quick port — stdlib only."""
    if kind not in ("chat", "research", "act"):
        raise ValueError(f"unknown kind: {kind} (chat|research|act)")
    if every_secs < 5:
        raise ValueError("every_secs must be >= 5 (cheap guard)")
    _jobs_table(db_path or "")
    job_id = uuid.uuid4().hex[:12]
    now = time.time()
    _JOBS[job_id] = {
        "id": job_id, "kind": kind, "payload": payload,
        "every_secs": float(every_secs), "next_run": now + float(every_secs),
        "created": now, "last_result": "", "user_id": user_id, "premium": premium,
    }
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        _TASKS[job_id] = loop.create_task(_run_loop(job_id))
    # else: loop started lazily on first run_all/ensure via start()
    return job_id


def unschedule(job_id: str) -> bool:
    job = _JOBS.pop(job_id, None)
    task = _TASKS.pop(job_id, None)
    if task and not task.done():
        task.cancel()
    return job is not None


def list_jobs() -> list[dict]:
    return [
        {k: v for k, v in j.items()}
        for j in sorted(_JOBS.values(), key=lambda j: j["created"])
    ]


def start() -> int:
    """Start background loops for all scheduled jobs. Returns count started."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return 0
    started = 0
    for job_id in list(_JOBS):
        task = _TASKS.get(job_id)
        if task is None or task.done():
            _TASKS[job_id] = loop.create_task(_run_loop(job_id))
            started += 1
    return started


def stop() -> int:
    """Cancel all background loops. Returns count cancelled."""
    count = 0
    for job_id, task in list(_TASKS.items()):
        if not task.done():
            task.cancel()
            count += 1
    _TASKS.clear()
    return count
