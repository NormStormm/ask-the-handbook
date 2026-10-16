"""The web page: a chat box for staff, plus an HR view of what the handbook couldn't answer.

    .venv/bin/python -m ask_handbook.app        # then open http://localhost:8000
"""
from __future__ import annotations

import csv
import pathlib

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from . import engine

ROOT = pathlib.Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
app = FastAPI(title="Ask the Handbook")
client = anthropic.Anthropic()


class Question(BaseModel):
    question: str


@app.get("/")
def index():
    return FileResponse(ROOT / "web" / "index.html")


@app.post("/api/ask")
def api_ask(q: Question):
    a = engine.ask(q.question, client)
    return {"status": a.status, "parts": a.parts, "sources": a.sources, "unsupported_numbers": a.unsupported_numbers,
            "seconds": a.seconds, "cost": round(a.cost, 5)}


@app.get("/api/unanswered")
def api_unanswered():
    path = ROOT / "logs" / "unanswered.csv"
    if not path.exists():
        return []
    with open(path) as f:
        return list(reversed(list(csv.DictReader(f))))[:200]


@app.get("/api/sections")
def api_sections():
    return [{"label": s.label} for doc in engine.DOCS for s in doc]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
