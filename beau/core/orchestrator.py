import os
from agents import Agent, Runner
from beau.core.config import OPENROUTER_MODEL, load_config
from beau.core.prompts import JARVIS_PROMPT

load_config()

def get_beau_agent():
    return Agent(name="BEAU", instructions=JARVIS_PROMPT, model=OPENROUTER_MODEL)

async def run_beau(prompt: str) -> str:
    agent = get_beau_agent()
    result = await Runner.run(agent, prompt)
    return result.final_output
