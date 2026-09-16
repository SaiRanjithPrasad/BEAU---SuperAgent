from fastapi import FastAPI, UploadFile
from pydantic import BaseModel
from beau.core.orchestrator import run_beau
from beau.tools.actor import act
from beau.tools.researcher import research
app = FastAPI(title="BEAU SuperAgent")

class ChatReq(BaseModel): message: str
class ChatResp(BaseModel): reply: str

class ResearchReq(BaseModel):
    query: str
class ResearchResp(BaseModel):
    report: str
    summary: str

@app.post("/v1/chat", response_model=ChatResp)
async def chat(req: ChatReq):
    reply = await run_beau(req.message)
    return ChatResp(reply=reply)

@app.post("/v1/audio/speech")
async def tts(req: ChatReq):
    from beau.voice.tts_provider import speak
    wav, provider = await speak(req.message)
    from fastapi.responses import Response
    return Response(content=wav, media_type="audio/wav", headers={"X-TTS-Provider": provider})

@app.post("/v1/audio/transcriptions")
async def stt(file: UploadFile):
    from beau.voice.stt.provider import get_stt
    data = await file.read()
    text = await get_stt().transcribe(data)
    return {"text": text}

@app.post("/v1/research", response_model=ResearchResp)
async def research_endpoint(req: ResearchReq):
    report = await research(req.query)
    return ResearchResp(report=report, summary=report[:200])

class ActReq(BaseModel):
    task: str
    success_criteria: str = ""

class ActResp(BaseModel):
    result: str
    needs_confirm: bool = False
    command: str = ""

@app.post("/v1/act", response_model=ActResp)
async def act_endpoint(req: ActReq):
    result = await act(req.task, req.success_criteria)
    needs = "needs_confirm" in result
    cmd = result.split("command:")[1].strip() if needs else ""
    return ActResp(result=result, needs_confirm=needs, command=cmd)

@app.post("/v1/act/confirm")
async def act_confirm(req: ActReq):
    # confirm destructive command — bypass guard and execute directly
    if req.success_criteria == "confirm":
        result = await act(req.task, req.success_criteria, confirmed=True)
        return ActResp(result=result, needs_confirm=False)
    return ActResp(result="not confirmed", needs_confirm=True, command=req.task)

@app.get("/health")
async def health(): return {"status": "ok"}
