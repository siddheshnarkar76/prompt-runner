"""
Orchestrator endpoints for chaining parsing -> classification -> calculator flows.
Provides a single POST /orchestrate/run entry point used by the UI and tests.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from agents.calculator_agent import calculator_agent
from agents.rule_classification_agent import classify_rules_for_city
from mcp.db import Collections, get_collection
from scripts.seed_rules import ensure_seed_rules

orchestrator_router = APIRouter()

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SUBJECT = {
    "height_m": 20.0,
    "setback_m": 3.5,
    "width_m": 24.0,
    "depth_m": 18.0,
    "floor_height_m": 3.0,
    "fsi": 1.8,
    "type": "residential",
}


class OrchestrateRequest(BaseModel):
    session_id: str = Field(..., min_length=3, description="Unique session identifier")
    city: str = Field(..., description="City name")
    prompt: str = Field(..., description="User prompt or design brief")
    subject: Dict[str, Any] = Field(default_factory=dict, description="Design subject parameters")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class OrchestrateResponse(BaseModel):
    success: bool
    session_id: str
    run_id: str
    outcomes: List[Dict[str, Any]]
    summary_id: Optional[str]
    timestamp: str
    warnings: List[str]


def _merge_subject(subject: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(DEFAULT_SUBJECT)
    for k, v in subject.items():
        if v is not None:
            merged[k] = v
    return merged


def _append_report(filename: str, data: Dict[str, Any]) -> None:
    try:
        path = REPORTS_DIR / filename
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
        else:
            payload = []
        payload.append(data)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        # Logging is best-effort; avoid failing the request
        pass


@orchestrator_router.post("/run", response_model=OrchestrateResponse)
async def orchestrate_run(request: OrchestrateRequest):
    """Run the end-to-end pipeline for a session."""
    try:
        run_id = (request.metadata or {}).get("run_id") if request.metadata else None
        run_id = run_id or f"run_{uuid4().hex[:10]}"
        timestamp = datetime.utcnow().isoformat() + "Z"

        ensure_seed_rules(request.city)

        # Classify any rules for the city (blocking, so run in thread pool)
        await run_in_threadpool(classify_rules_for_city, request.city)

        subject = _merge_subject(request.subject)
        outcomes = await run_in_threadpool(calculator_agent, request.city, subject)

        evaluations = get_collection(Collections.EVALUATIONS)
        record = {
            "session_id": request.session_id,
            "run_id": run_id,
            "city": request.city,
            "prompt": request.prompt,
            "subject": subject,
            "outcomes": outcomes,
            "metadata": request.metadata or {},
            "timestamp": timestamp,
        }
        res = evaluations.insert_one(record)

        _append_report("run_logs.json", record)

        return OrchestrateResponse(
            success=True,
            session_id=request.session_id,
            run_id=run_id,
            outcomes=outcomes,
            summary_id=str(res.inserted_id),
            timestamp=timestamp,
            warnings=[],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Orchestration failed: {exc}")
