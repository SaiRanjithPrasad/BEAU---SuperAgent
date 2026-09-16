from agents import Agent, Runner, function_tool
import asyncio
from beau.core.config import OPENROUTER_MODEL, load_config
from beau.core.prompts import JARVIS_PROMPT
from beau.tools.actor import act
from beau.tools.researcher import research

load_config()

@function_tool
def research_tool(query: str) -> str:
    """Research a query using lean planner→search→writer pipeline (cheap, knowledge-only)."""
    return asyncio.run(research(query))

@function_tool
def act_tool(task: str, success_criteria: str = "") -> str:
    """Act on a task using sandboxed sidekick (file+shell+full tools) with human_confirm."""
    return asyncio.run(act(task, success_criteria))

def get_beau_agent():
    return Agent(name="BEAU", instructions=JARVIS_PROMPT, model=OPENROUTER_MODEL, tools=[research_tool, act_tool])

async def run_beau(prompt: str) -> str:
    agent = get_beau_agent()
    result = await Runner.run(agent, prompt)
    return result.final_output
