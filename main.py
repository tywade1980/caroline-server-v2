import os
import json
import logging
import traceback
import requests
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("caroline")

app = FastAPI(title="Caroline AI Server v2", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

@app.get("/health")
def health():
    return {
        "status": "online",
        "keys": {
            "xai": bool(XAI_API_KEY),
            "openrouter": bool(OPENROUTER_API_KEY),
            "elevenlabs": bool(ELEVENLABS_API_KEY)
        }
    }

@app.post("/token")
def mint_token():
    """Mint ephemeral xAI Realtime token"""
    if not XAI_API_KEY:
        raise HTTPException(status_code=500, detail="XAI_API_KEY missing")
    try:
        resp = requests.post(
            "https://api.x.ai/v1/realtime/client_secrets",
            headers={"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"},
            json={"expires_after": {"seconds": 300}},
            timeout=10
        )
        resp.raise_for_status()
        return {"token": resp.json()["value"], "expires_at": resp.json()["expires_at"]}
    except Exception as e:
        log.error(f"Token error: {e}")
        raise HTTPException(status_code=502, detail=str(e))

@app.post("/llm")
async def llm_relay(request: Request):
    """Relay to OpenRouter"""
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY missing")
    body = await request.json()
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
            json=body,
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.post("/tts")
async def tts_relay(request: Request):
    """Relay to ElevenLabs"""
    if not ELEVENLABS_API_KEY:
        raise HTTPException(status_code=500, detail="ELEVENLABS_API_KEY missing")
    body = await request.json()
    text = body.get("text", "")
    voice_id = body.get("voice_id", "EXAVITQu4vr4xnSDxMaL") # Default voice
    try:
        resp = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"},
            json={"text": text, "model_id": "eleven_turbo_v2_5"},
            timeout=30
        )
        resp.raise_for_status()
        return Response(content=resp.content, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

@app.get("/")
def root():
    return HTMLResponse("<h1>Caroline AI Server v2 (Railway)</h1><p>Status: Online</p>")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
