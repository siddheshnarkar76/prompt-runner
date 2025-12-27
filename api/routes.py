"""
API Routes - CreatorCore and MCP Endpoints
All REST API endpoints for the AI Design Platform.
"""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import json
from pathlib import Path

from mcp.schemas import (
    CoreLogRequest, CoreLogResponse,
    CoreFeedbackRequest, CoreFeedbackResponse,
    CoreContextResponse,
    SaveRuleRequest,
    GeometryRequest,
    MCPFeedbackRequest
)
from mcp.db import get_collection, Collections
from agents.compliance_pipeline import run_compliance_pipeline

logger = logging.getLogger(__name__)

# Create routers
core_router = APIRouter()
mcp_router = APIRouter()

# Reports directory for local logging
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# CreatorCore Integration Endpoints
# ============================================================================

@core_router.post("/log", response_model=CoreLogResponse)
async def core_log(request: CoreLogRequest):
    """
    POST /core/log
    Submit design output for compliance logging.
    
    This endpoint receives design prompts and runs them through the
    compliance pipeline (MANDATORY FIXES version) to produce decision-ready,
    traceable, deterministic output.
    """
    try:
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Run compliance pipeline on the prompt
        city = request.city or "Generic"
        pipeline_output = run_compliance_pipeline(
            prompt=request.prompt,
            city=city,
            rules=[]  # Pipeline loads rules from mcp_data/rules.json
        )
        
        # Extract case_id from pipeline output
        case_id = pipeline_output.get("case_id", request.session_id)
        
        # Create log document with pipeline results
        log_doc = {
            "case_id": case_id,
            "session_id": request.session_id,
            "prompt": request.prompt,
            "city": city,
            "event": request.event or "compliance_check",
            "pipeline_status": pipeline_output.get("status"),
            "pipeline_output": pipeline_output,  # Full pipeline output
            "output": request.output or pipeline_output,  # Fallback to pipeline output
            "timestamp": timestamp,
            "metadata": request.metadata or {}
        }
        
        # Store in MongoDB
        core_logs_col = get_collection(Collections.CORE_LOGS)
        result = core_logs_col.insert_one(log_doc)
        
        # Also store in local reports for offline access
        _append_to_report("core_bridge_runs.json", log_doc)
        
        logger.info(f"Core log stored with compliance pipeline: case_id={case_id}, status={pipeline_output.get('status')}, city={city}")
        
        return CoreLogResponse(
            success=True,
            session_id=case_id,  # Return case_id from pipeline
            logged=True,
            timestamp=timestamp
        )
        
    except Exception as e:
        logger.error(f"Core log failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to log: {str(e)}")


@core_router.post("/feedback", response_model=CoreFeedbackResponse)
async def core_feedback(request: CoreFeedbackRequest):
    """
    POST /core/feedback
    Submit user feedback for RL training.
    
    This endpoint receives user feedback (thumbs up/down) and triggers
    reinforcement learning policy updates.
    """
    try:
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Extract city from metadata
        city = request.metadata.get("city", "Unknown") if request.metadata else "Unknown"
        
        # Create feedback document
        feedback_doc = {
            "session_id": request.session_id,
            "prompt": request.prompt or "",
            "output": request.output or {},
            "feedback": request.feedback,
            "city": city,
            "timestamp": timestamp,
            "reward": request.feedback,  # Simple reward = feedback
            "metadata": request.metadata or {}
        }
        
        # Store in MongoDB
        creator_feedback_col = get_collection(Collections.CREATOR_FEEDBACK)
        creator_feedback_col.insert_one(feedback_doc)
        
        # Update RL agent policy
        confidence_score = await _update_rl_policy(request.session_id, request.feedback, request.output, city)
        
        # Store in feedback flow report
        _append_to_report("feedback_flow.json", {
            "session_id": request.session_id,
            "feedback": request.feedback,
            "city": city,
            "reward": request.feedback,
            "timestamp": timestamp,
            "rl_update": True
        })
        
        logger.info(f"Feedback stored: session_id={request.session_id}, feedback={request.feedback}")
        
        return CoreFeedbackResponse(
            success=True,
            reward=request.feedback,
            confidence_score=confidence_score,
            rl_learning_active=True
        )
        
    except Exception as e:
        logger.error(f"Core feedback failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to store feedback: {str(e)}")


@core_router.get("/context", response_model=CoreContextResponse)
async def core_context(
    session_id: str = Query(..., description="Session identifier"),
    limit: int = Query(10, ge=1, le=100, description="Maximum entries to return")
):
    """
    GET /core/context
    Retrieve historical context for a session.
    
    Returns previous logs and feedback for cumulative scoring before next run.
    """
    try:
        # Get logs from core_logs collection
        core_logs_col = get_collection(Collections.CORE_LOGS)
        entries = list(
            core_logs_col.find(
                {"session_id": session_id},
                {"_id": 0}  # Exclude MongoDB _id
            )
            .sort("timestamp", -1)
            .limit(limit)
        )
        
        logger.info(f"Context retrieved: session_id={session_id}, count={len(entries)}")
        
        return CoreContextResponse(
            success=True,
            session_id=session_id,
            entries=entries,
            count=len(entries)
        )
        
    except Exception as e:
        logger.error(f"Core context failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve context: {str(e)}")


# ============================================================================
# MCP Legacy Endpoints (Preserved for backward compatibility)
# ============================================================================

@mcp_router.post("/save_rule")
async def save_rule(request: SaveRuleRequest):
    """POST /api/mcp/save_rule - Save a city rule."""
    try:
        rules_col = get_collection(Collections.RULES)
        
        rule_doc = {
            "city": request.city,
            "rule_id": request.rule_id,
            "rule_text": request.rule_text,
            "category": request.category,
            "parsed_data": request.parsed_data,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        # Upsert to avoid duplicates
        rules_col.update_one(
            {"city": request.city, "rule_id": request.rule_id},
            {"$set": rule_doc},
            upsert=True
        )
        
        logger.info(f"Rule saved: city={request.city}, rule_id={request.rule_id}")
        
        return {"success": True, "rule_id": request.rule_id}
        
    except Exception as e:
        logger.error(f"Save rule failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.get("/list_rules")
async def list_rules(city: Optional[str] = Query(None)):
    """GET /api/mcp/list_rules - List rules for a city."""
    try:
        rules_col = get_collection(Collections.RULES)
        
        query = {"city": city} if city else {}
        rules = list(rules_col.find(query, {"_id": 0}))
        
        return {"success": True, "rules": rules, "count": len(rules)}
        
    except Exception as e:
        logger.error(f"List rules failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.post("/geometry")
async def save_geometry(request: GeometryRequest):
    """POST /api/mcp/geometry - Save geometry output."""
    try:
        geometry_col = get_collection(Collections.GEOMETRY_OUTPUTS)
        
        geo_doc = {
            "case_id": request.case_id,
            "geometry_data": request.geometry_data,
            "city": request.city,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        geometry_col.insert_one(geo_doc)
        
        logger.info(f"Geometry saved: case_id={request.case_id}")
        
        return {"success": True, "case_id": request.case_id}
        
    except Exception as e:
        logger.error(f"Save geometry failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.post("/feedback")
async def mcp_feedback(request: MCPFeedbackRequest):
    """POST /api/mcp/feedback - Legacy feedback endpoint."""
    try:
        feedback_col = get_collection(Collections.FEEDBACK)
        
        feedback_doc = {
            "case_id": request.case_id,
            "feedback": request.feedback,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "metadata": request.metadata or {}
        }
        
        feedback_col.insert_one(feedback_doc)
        
        logger.info(f"Legacy feedback saved: case_id={request.case_id}")
        
        return {"success": True, "reward": request.feedback}
        
    except Exception as e:
        logger.error(f"MCP feedback failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@mcp_router.get("/creator_feedback/session/{session_id}")
async def get_creator_feedback(session_id: str):
    """GET /api/mcp/creator_feedback/session/{session_id} - Get feedback history."""
    try:
        creator_feedback_col = get_collection(Collections.CREATOR_FEEDBACK)
        
        feedback_list = list(
            creator_feedback_col.find(
                {"session_id": session_id},
                {"_id": 0}
            ).sort("timestamp", -1)
        )
        
        return {"success": True, "feedback": feedback_list, "count": len(feedback_list)}
        
    except Exception as e:
        logger.error(f"Get creator feedback failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Helper Functions
# ============================================================================

async def _update_rl_policy(session_id: str, feedback: int, output: Optional[Dict], city: str) -> float:
    """
    Update RL policy based on feedback.
    Returns confidence score.
    """
    try:
        # Import RL agent functions
        from agents.rl_agent import get_rl_policy
        
        # Extract parameters from output
        if output and "parameters" in output:
            parameters = output["parameters"]
        elif output and "subject" in output:
            parameters = output["subject"]
        else:
            parameters = output or {}
        
        # Get policy and update
        policy = get_rl_policy()
        if parameters:
            policy.update(
                city=city,
                parameters=parameters,
                reward=feedback,
                param_type=parameters.get("type", "residential")
            )
            # Save policy
            from agents.rl_agent import POLICY_FILE
            policy.save(POLICY_FILE)
        
        # Calculate confidence score
        creator_feedback_col = get_collection(Collections.CREATOR_FEEDBACK)
        feedback_history = list(creator_feedback_col.find({"session_id": session_id}))
        
        if not feedback_history:
            return 0.0
        
        total = sum(f.get("feedback", 0) for f in feedback_history)
        confidence = round(total / len(feedback_history), 2)
        
        return confidence
        
    except Exception as e:
        logger.warning(f"RL policy update failed: {e}")
        return 0.0


def _append_to_report(filename: str, data: Dict[str, Any]):
    """Append data to a JSON report file."""
    try:
        report_path = REPORTS_DIR / filename
        
        # Load existing data
        if report_path.exists():
            with open(report_path, "r") as f:
                reports = json.load(f)
        else:
            reports = []
        
        # Append new data
        reports.append(data)
        
        # Save back
        with open(report_path, "w") as f:
            json.dump(reports, f, indent=2)
            
    except Exception as e:
        logger.warning(f"Failed to append to report {filename}: {e}")
