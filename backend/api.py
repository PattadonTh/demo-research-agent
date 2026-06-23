"""
api.py — FastAPI server for the Research Agent
================================================
Endpoints:
  POST /run                — Start a research task
  GET  /status/{thread_id} — Poll task status + result
  POST /review/{thread_id} — Approve or reject (HITL)
  GET  /history            — List all past runs
  GET  /health             — Health check
"""

import asyncio
import uuid
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

load_dotenv()  # must run before LangChain imports so LangSmith tracing env vars are set

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import AgentOutput
from main import build_graph, _init_state

app = FastAPI(title="Research Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to Vercel domain in prod
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── In-memory thread store ───────────────────────────────────────────────────

_threads: dict[str, dict] = {}


# ─── Request / Response models ────────────────────────────────────────────────


class RunRequest(BaseModel):
    task: str
    hitl: bool = False


class ReviewRequest(BaseModel):
    action: str  # "approve" | "reject"
    feedback: Optional[str] = None


# ─── Background runners ───────────────────────────────────────────────────────


async def _run_graph(thread_id: str, task: str) -> None:
    info = _threads[thread_id]
    graph = info["graph"]
    config = info["config"]
    try:
        await graph.ainvoke(_init_state(task), config=config)
        snapshot = graph.get_state(config)
        if snapshot.next:
            # Interrupted before human_review — awaiting review
            info["status"] = "waiting_review"
            info["result"] = snapshot.values.get("result")
        else:
            info["status"] = "completed"
            info["result"] = snapshot.values.get("result")
    except Exception as e:
        info["status"] = "failed"
        info["error"] = str(e)


async def _resume_graph(thread_id: str) -> None:
    info = _threads[thread_id]
    graph = info["graph"]
    config = info["config"]
    try:
        await graph.ainvoke(None, config=config)
        snapshot = graph.get_state(config)
        if snapshot.next:
            # Rejected → re-ran agent → paused at human_review again
            info["status"] = "waiting_review"
            info["result"] = snapshot.values.get("result")
        else:
            info["status"] = "completed"
            info["result"] = snapshot.values.get("result")
    except Exception as e:
        info["status"] = "failed"
        info["error"] = str(e)


# ─── Endpoints ────────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/run", status_code=202)
async def run(req: RunRequest):
    """Start a research task. Returns thread_id immediately; poll /status/{thread_id}."""
    thread_id = str(uuid.uuid4())
    graph = build_graph(use_hitl=req.hitl)
    config = {"configurable": {"thread_id": thread_id}}

    _threads[thread_id] = {
        "thread_id": thread_id,
        "task": req.task,
        "status": "running",
        "result": None,
        "error": None,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "graph": graph,
        "config": config,
        "use_hitl": req.hitl,
    }

    asyncio.create_task(_run_graph(thread_id, req.task))
    return {"thread_id": thread_id, "status": "running"}


@app.get("/status/{thread_id}")
async def status(thread_id: str):
    """
    Poll task status.
    status values: running | waiting_review | completed | failed
    result is populated when status == 'completed' or 'waiting_review'.
    """
    info = _threads.get(thread_id)
    if not info:
        raise HTTPException(status_code=404, detail="Thread not found")

    result: Optional[AgentOutput] = info["result"]
    return {
        "thread_id": thread_id,
        "task": info["task"],
        "status": info["status"],
        "result": result.model_dump() if result else None,
        "error": info["error"],
        "created_at": info["created_at"],
    }


@app.post("/review/{thread_id}")
async def review(thread_id: str, req: ReviewRequest):
    """
    Approve or reject a result waiting for human review (hitl=true only).
    - action: 'approve' → saves and completes
    - action: 'reject'  → reruns agent with feedback (requires feedback field)
    """
    info = _threads.get(thread_id)
    if not info:
        raise HTTPException(status_code=404, detail="Thread not found")
    if info["status"] != "waiting_review":
        raise HTTPException(
            status_code=400,
            detail=f"Thread is not awaiting review (current status: {info['status']})",
        )
    if req.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")
    if req.action == "reject" and not req.feedback:
        raise HTTPException(status_code=400, detail="feedback is required when rejecting")

    graph = info["graph"]
    config = info["config"]

    if req.action == "approve":
        graph.update_state(config, {"status": "approved"}, as_node="human_review")
    else:
        graph.update_state(
            config,
            {"status": "rejected", "feedback": req.feedback},
            as_node="human_review",
        )

    info["status"] = "running"
    asyncio.create_task(_resume_graph(thread_id))
    return {"thread_id": thread_id, "status": "running"}


@app.get("/history")
async def history():
    """List all research tasks started in this server session."""
    return [
        {
            "thread_id": t["thread_id"],
            "task": t["task"],
            "status": t["status"],
            "created_at": t["created_at"],
            "title": t["result"].title if t["result"] else None,
        }
        for t in _threads.values()
    ]
