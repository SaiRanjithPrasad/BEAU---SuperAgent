from beau.tools.actor.sidekick import Sidekick

async def act(task: str, success_criteria: str = "") -> str:
    s = Sidekick()
    return await s.run(task, success_criteria)
