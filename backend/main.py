
import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from dotenv import load_dotenv
from openai import OpenAI

# Load environment settings
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"

# Create application
app = FastAPI(
    title="NaijaVoice AI",
    description="Nigerian Voice Transcription API",
    version="1.0.0"
)

# Connect to OpenAI when an API key is available
client = OpenAI(api_key=api_key) if api_key else None

@app.get("/")
def home():
    return {
        "message": "Welcome to NaijaVoice AI Backend!",
        "status": "running"
    }

@app.get("/health")
def health_check():
    return {
        "status": "online",
        "project": "NaijaVoice AI"
    }

@app.get("/api-status")
def api_status():
    return {
        "api_key_configured": bool(api_key),
        "demo_mode": demo_mode
    }

@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):

    try:
        if not audio.content_type or not audio.content_type.startswith("audio/"):
            raise HTTPException(
                status_code=400,
                detail="Please upload a valid audio file."
            )

        contents = await audio.read()

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="The audio file is empty."
            )

        if len(contents) > 25 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="Audio file must not exceed 25 MB."
            )

        # DEMO MODE
        if demo_mode:
            return {
                "success": True,
                "mode": "demo",
                "transcription": (
                    "Good morning everyone. Please remember "
                    "that our group meeting will hold tomorrow. "
                    "Everyone should prepare their project updates."
                ),
                "message": "This is sample text, not a real transcription."
            }

        # REAL AI TRANSCRIPTION
        if not client:
            raise HTTPException(
                status_code=500,
                detail="OpenAI API key is missing."
            )

        transcription = client.audio.transcriptions.create(
            model="gpt-transcribe",
            file=(
                audio.filename or "recording.webm",
                contents,
                audio.content_type
            )
        )

        return {
            "success": True,
            "mode": "real",
            "transcription": transcription.text
        }

    finally:
        await audio.close()