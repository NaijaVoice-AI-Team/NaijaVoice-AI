import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"

# Models are configurable from .env so you can change them without editing code.
# Check OpenAI's model list if a name is rejected.
TRANSCRIBE_MODEL = os.getenv("TRANSCRIBE_MODEL", "gpt-4o-transcribe")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")

MAX_AUDIO_BYTES = 25 * 1024 * 1024
AUDIO_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg", ".flac"}

app = FastAPI(
    title="NaijaVoice AI",
    description="Nigerian Voice Transcription API",
    version="1.1.0",
)

# Allow the frontend (opened from a file or another port) to call this API.
# For production, replace "*" with your real frontend URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=api_key) if api_key else None


@app.get("/")
def home():
    return {"message": "Welcome to NaijaVoice AI Backend!", "status": "running"}


@app.get("/health")
def health_check():
    return {"status": "online", "project": "NaijaVoice AI"}


@app.get("/api-status")
def api_status():
    return {"api_key_configured": bool(api_key), "demo_mode": demo_mode}


def _looks_like_audio(audio: UploadFile) -> bool:
    ctype = (audio.content_type or "").lower()
    ext = os.path.splitext(audio.filename or "")[1].lower()
    return ctype.startswith("audio/") or ctype.startswith("video/webm") or ext in AUDIO_EXTENSIONS


def _transcribe(filename: str, contents: bytes, content_type: str) -> str:
    result = client.audio.transcriptions.create(
        model=TRANSCRIBE_MODEL,
        file=(filename, contents, content_type),
    )
    return result.text


def _pidgin_to_english(text: str) -> str:
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You convert Nigerian Pidgin English into clear, standard English. "
                    "Keep the meaning, names and numbers exactly. "
                    "If the text is already standard English, return it unchanged. "
                    "Return only the converted text, nothing else."
                ),
            },
            {"role": "user", "content": text},
        ],
        temperature=0,
    )
    return response.choices[0].message.content.strip()


@app.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    to_english: bool = Form(False),
):
    try:
        if not _looks_like_audio(audio):
            raise HTTPException(status_code=400, detail="Please upload a valid audio file.")

        contents = await audio.read()

        if not contents:
            raise HTTPException(status_code=400, detail="The audio file is empty.")

        if len(contents) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=413, detail="Audio file must not exceed 25 MB.")

        if demo_mode:
            return {
                "success": True,
                "mode": "demo",
                "transcription": (
                    "Good morning everyone. Please remember "
                    "that our group meeting will hold tomorrow. "
                    "Everyone should prepare their project updates."
                ),
                "message": "This is sample text, not a real transcription.",
            }

        if not client:
            raise HTTPException(status_code=500, detail="OpenAI API key is missing.")

        try:
            # Run the blocking OpenAI calls in a worker thread so the server stays responsive.
            text = await run_in_threadpool(
                _transcribe,
                audio.filename or "recording.webm",
                contents,
                audio.content_type or "audio/webm",
            )
            response = {"success": True, "mode": "real", "transcription": text}

            if to_english and text:
                response["english"] = await run_in_threadpool(_pidgin_to_english, text)

            return response
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Transcription service error: {exc}")

    finally:
        await audio.close()
