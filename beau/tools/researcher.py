import asyncio
from agents import Runner
from beau.tools.research.planner import planner_agent, WebSearchPlan
from beau.tools.research.search import search_agent
from beau.tools.research.writer import writer_agent, ReportData

async def research(query: str) -> str:
    # 1. planner
    try:
        plan_result = await Runner.run(planner_agent, query)
        plan: WebSearchPlan = plan_result.final_output
        searches = plan.searches[:3] if plan and plan.searches else []
        if not searches:
            from beau.tools.research.planner import WebSearchItem
            searches = [WebSearchItem(reason="fallback", query=query)]
    except Exception:
        from beau.tools.research.planner import WebSearchItem
        searches = [WebSearchItem(reason="fallback", query=query)]

    # 2. search ×3 gather
    summaries = []
    for item in searches:
        try:
            r = await Runner.run(search_agent, item.query)
            summaries.append(r.final_output if isinstance(r.final_output, str) else str(r.final_output))
        except Exception as e:
            summaries.append(f"[Search error for {item.query}: {e}]")

    research_text = "\n\n".join(summaries)

    # 3. writer
    try:
        writer_input = f"Query: {query}\n\nResearch:\n{research_text}"
        w = await Runner.run(writer_agent, writer_input)
        report: ReportData = w.final_output
        markdown = report.markdown_report
    except Exception:
        markdown = research_text  # fallback

    # 4. memory best-effort
    try:
        from beau.memory.store import MemoryStore
        MemoryStore().save(query, markdown[:2000])
    except Exception:
        pass

    return markdown

# for tests that need full object
async def research_full(query: str) -> ReportData:
    md = await research(query)
    return ReportData(short_summary=md[:200], markdown_report=md, follow_up_questions=[])
