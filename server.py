"""
server.py
Lightweight API that wraps the existing pipeline (transcribe -> diarize
-> analyze) so the UI can upload a new recording and get the full report
back.

IMPORTANT: the pipeline can take several minutes per call. A hosted server
will kill a request that hangs that long, so this does NOT run the pipeline
inside the request. Instead:
  1. POST /process-call saves the file, starts the pipeline in the
     background, and returns a job_id immediately.
  2. The client polls GET /status/{job_id} every few seconds until the
     job's status is "done" (or "error").
This means the person using the UI doesn't have to keep one browser tab
open and waiting on a single long request - it also survives the request
timeout limits most hosting platforms enforce.

Run with:
    uvicorn server:app --reload --port 8000
"""

import os
import shutil
import uuid

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from main import run_pipeline

RAW_AUDIO_DIR = "data/raw_audio"

app = FastAPI()

# Allows the frontend (running on a different domain/port) to call this
# API. Fine for a small personal/internship tool; tighten allow_origins
# to your actual frontend URL once deployed if you want it locked down.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job tracking: {job_id: {"status": ..., "result": ..., "error": ...}}
# This resets if the server restarts - fine for a small prototype. If this
# becomes a real product, swap it for a database or Redis so jobs survive
# restarts and work across multiple server instances.
JOBS: dict[str, dict] = {}


def _run_job(job_id: str, save_path: str):
    """Runs the full pipeline and stores the result under the job id."""
    try:
        result = run_pipeline(save_path)
        JOBS[job_id] = {"status": "done", "result": result}
    except Exception as e:
        JOBS[job_id] = {"status": "error", "error": str(e)}


@app.post("/process-call")
async def process_call(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Accepts an uploaded audio/video file and starts processing it in the
    background. Returns immediately with a job_id to poll.
    """
    os.makedirs(RAW_AUDIO_DIR, exist_ok=True)
    save_path = os.path.join(RAW_AUDIO_DIR, file.filename)

    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "processing"}
    background_tasks.add_task(_run_job, job_id, save_path)

    return {"job_id": job_id}


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """
    Poll this to check on a job. Returns one of:
      {"status": "processing"}
      {"status": "done", "result": {...}}
      {"status": "error", "error": "..."}
    """
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/health")
async def health():
    """Quick check the server is up: GET /health"""
    return {"status": "ok"}