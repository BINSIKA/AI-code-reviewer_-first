"""
server.py
FastAPI REST API server — exposes the analysis pipeline as HTTP endpoints.
Run with:  uvicorn server:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys, os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from analyzer import run_full_analysis, run_chat

app = FastAPI(
    title="AI Code Reviewer API",
    description="REST API for static analysis + AI code review using Groq LLaMA",
    version="1.0.0",
)

# Allow Reflex frontend (localhost:3000) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────
#  Request / Response models
# ─────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    code: str
    language: str = "python"


class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = ""
    history: Optional[list] = []


class AnalyzeResponse(BaseModel):
    language: str
    language_display: str
    syntax_status: str
    syntax_msg: str
    unused_imports: list
    unused_functions: list
    unused_variables: list
    style_violations: list
    created_vars: list
    used_vars: list
    linter_tools: list
    issues: list
    issue_count: int
    grade: str
    summary: str
    corrected_code: str
    optimizations: list
    detected_bugs: list


# ─────────────────────────────────────────
#  Endpoints
# ─────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "message": "AI Code Reviewer API is running."}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    """
    Run full analysis pipeline on submitted code.
    Returns syntax, static, and AI results.
    """
    if not req.code or not req.code.strip():
        raise HTTPException(status_code=400, detail="No code provided.")

    try:
        result = run_full_analysis(req.code, req.language)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
def chat(req: ChatRequest):
    """
    Send a message to the AI assistant with analysis context.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Empty message.")

    try:
        reply = run_chat(req.message, req.context, req.history)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "healthy"}


# ─────────────────────────────────────────
#  Dev run
# ─────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
