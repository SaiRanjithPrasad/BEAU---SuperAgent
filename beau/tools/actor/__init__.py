from beau.tools.actor.sidekick import Sidekick

async def act(task: str, success_criteria: str = "", confirmed: bool = False) -> str:
    s = Sidekick()
    return await s.run(task, success_criteria, confirmed=confirmed)
