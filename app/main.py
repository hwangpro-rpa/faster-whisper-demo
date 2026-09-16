import logging
import os
import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from faster_whisper import WhisperModel

from .audio_prep import load_and_clean_audio
from .grader import get_grader
from .items import get_item, get_items, hotwords_for

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-grader")

WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "small")
DEMO_TOKEN = os.environ.get("DEMO_TOKEN")  # optional simple shared-secret gate for public tunnel use

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

model: WhisperModel | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    logger.info("Loading faster-whisper model=%s (CPU, int8)...", WHISPER_MODEL_SIZE)
    model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    logger.info("Model loaded.")
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _check_token(token: str | None):
    if DEMO_TOKEN and token != DEMO_TOKEN:
        raise HTTPException(status_code=401, detail="invalid or missing token")


@app.get("/api/items")
def list_items():
    return [
        {"id": item.id, "language": item.language, "text": item.text, "level": item.level}
        for item in get_items()
    ]


@app.post("/api/grade")
async def grade(
    item_id: str = Form(...),
    audio: UploadFile = File(...),
    token: str | None = Form(default=None),
):
    _check_token(token)

    item = get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="unknown item_id")

    suffix = os.path.splitext(audio.filename or "")[1] or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        assert model is not None
        audio_array = load_and_clean_audio(tmp_path)
        segments, _info = model.transcribe(
            audio_array,
            language=item.language,
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
            hotwords=hotwords_for(item.language),
        )
        recognized_text = "".join(seg.text for seg in segments).strip()
    finally:
        os.unlink(tmp_path)

    grader = get_grader()
    result = grader.grade(item.text, recognized_text, item.language)

    return {
        "item_id": item.id,
        "target_text": item.text,
        "recognized_text": recognized_text,
        "correct": result.correct,
        "diff_ops": result.diff_ops,
        "feedback": result.feedback,
        "grader": result.provider,
    }


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
