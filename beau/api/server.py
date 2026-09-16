from fastapi import FastAPI, UploadFile
from pydantic import BaseModel
from beau.core.orchestrator import run_beau
app = FastAPI(title="BEAU SuperAgent")

class ChatReq(BaseModel): message: str
class ChatResp(BaseModel): reply: str

@app.post("/v1/chat", response_model=ChatResp)
async def chat(req: ChatReq):
    reply = await run_beau(req.message)
    return ChatResp(reply=reply)

@app.post("/v1/audio/speech")
async def tts(req: ChatReq):
    from beau.voice.fish_audio.client import FishAudioClient
    c = FishAudioClient()
    wav = await c.tts(req.message)
    from fastapi.responses import Response
    return Response(content=wav, media_type="audio/wav")

@app.post("/v1/audio/transcriptions")
async def stt(file: UploadFile):
    from beau.voice.stt.provider import get_stt
    data = await file.read()
    text = await get_stt().transcribe(data)
    return {"text": text}

@app.get("/health")
async def health(): return {"status": "ok"}
