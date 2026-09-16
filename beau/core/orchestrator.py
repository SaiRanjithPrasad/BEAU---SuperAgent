from agents import Agent, Runner, function_tool
from agents.models.multi_provider import MultiProvider
from agents.run_config import RunConfig
import asyncio
import os
from beau.core.config import OPENROUTER_MODEL, load_config
from beau.core.prompts import JARVIS_PROMPT
from beau.tools.actor import act
from beau.tools.researcher import research
from beau.tools.scheduler import schedule, unschedule, list_jobs

load_config()

def _run_async(coro):
    """Run coroutine safely whether or not an event loop is already running."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)

@function_tool
def research_tool(query: str) -> str:
    """Research a query using lean planner→search→writer pipeline (cheap, knowledge-only)."""
    return _run_async(research(query))
@function_tool
def act_tool(task: str, success_criteria: str = "") -> str:
    """Act on a task using sandboxed sidekick (file+shell+full tools) with human_confirm."""
    return _run_async(act(task, success_criteria))


@function_tool
def schedule_tool(kind: str, payload: str, every_secs: float, user_id: str = "local", premium: bool = False) -> str:
    """Schedule a recurring BEAU job (chat/research/act). Returns job_id."""
    return schedule(kind, payload, every_secs, user_id, premium)


@function_tool
def unschedule_tool(job_id: str) -> str:
    """Cancel a scheduled job."""
    return "ok" if unschedule(job_id) else "unknown job"


@function_tool
def list_jobs_tool() -> str:
    """List scheduled jobs."""
    import json
    return json.dumps(list_jobs())


def get_beau_agent():
    return Agent(name="BEAU", instructions=JARVIS_PROMPT, model=OPENROUTER_MODEL, tools=[research_tool, act_tool, schedule_tool, unschedule_tool, list_jobs_tool])


def _get_run_config():
    provider = MultiProvider(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        unknown_prefix_mode="model_id",
    )
    return RunConfig(model=OPENROUTER_MODEL, model_provider=provider)

async def run_beau(prompt: str) -> str:
    agent = get_beau_agent()
    result = await Runner.run(agent, prompt, run_config=_get_run_config())
    return result.final_output
