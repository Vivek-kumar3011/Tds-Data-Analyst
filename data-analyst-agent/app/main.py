
import os, io, time, zipfile, json
from typing import Dict
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.runners import wiki_top_grossing, indian_high_court, generic_csv

app = FastAPI(title="Data Analyst Agent API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RUNNERS = [wiki_top_grossing, indian_high_court, generic_csv]

def pick_runner(task_text: str):
    for r in RUNNERS:
        try:
            if r.can_handle(task_text):
                # wiki and indian runners are guarded by their own can_handle
                # generic_csv always returns True, so keep it last.
                return r
        except Exception:
            continue
    return generic_csv

@app.post("/api/")
async def analyze_api(questions: UploadFile = File(...), files: list[UploadFile] = File(default=[])):
    """
    Accepts multipart/form-data. 'questions' is required (questions.txt).
    Any other attached files are available to runners.
    Returns JSON of answers per the prompt.
    """
    start_time = time.monotonic()
    try:
        task_text = (await questions.read()).decode("utf-8", errors="ignore")
    except Exception:
        task_text = ""
    # Load other files into memory (name -> bytes)
    file_bytes: Dict[str, bytes] = {}
    for f in files or []:
        try:
            b = await f.read()
            file_bytes[f.filename] = b
        except Exception:
            continue
    runner = pick_runner(task_text)
    try:
        answers = runner.run(task_text, file_bytes, start_time)
    except Exception as e:
        # Always return something
        answers = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    return JSONResponse(content=answers)
