from agents import Agent, WebSearchTool, ModelSettings
import os
from beau.core.config import OPENROUTER_MODEL
INSTRUCTIONS = """
You are a research assistant. Given a search term, you search the web for that term and 
produce a concise summary of the results. The summary must 2-3 paragraphs and less than 300 words.
Capture the main points and be succinct. Reply only with the summary.
"""
if os.getenv("OPENROUTER_API_KEY"):
    tools = []
    settings = ModelSettings()
else:
    settings = ModelSettings(tool_choice="required")
    tools = [WebSearchTool()]
search_agent = Agent(name="Search Agent", instructions=INSTRUCTIONS, tools=tools, model=OPENROUTER_MODEL, model_settings=settings)
