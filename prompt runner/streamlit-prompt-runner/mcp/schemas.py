"""
MCP Data Schemas
Pydantic models for request/response validation.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class FeedbackValue(int, Enum):
    """Valid feedback values: 1 (positive) or -1 (negative)."""
    POSITIVE = 1
    NEGATIVE = -1


# ============================================================================
# CreatorCore API Schemas
# ============================================================================

class CoreLogRequest(BaseModel):
    """Request schema for POST /core/log"""
    session_id: str = Field(..., min_length=8, description="Unique session identifier")
    city: str = Field(..., description="City name (Mumbai, Pune, etc.)")
    prompt: str = Field(..., description="Original user prompt")
    output: Dict[str, Any] = Field(..., description="Generated output JSON")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")
    event: Optional[str] = Field(default="prompt_submitted", description="Event type")
    
    @field_validator('city')
    @classmethod
    def validate_city(cls, v):
        valid_cities = ['Mumbai', 'Pune', 'Nashik', 'Ahmedabad']
        if v not in valid_cities:
            # Don't fail validation, just log warning
            pass
        return v


class CoreLogResponse(BaseModel):
    """Response schema for POST /core/log"""
    success: bool
    session_id: str
    logged: bool
    timestamp: str


class CoreFeedbackRequest(BaseModel):
    """Request schema for POST /core/feedback"""
    session_id: str = Field(..., min_length=8, description="Session identifier")
    feedback: int = Field(..., description="Feedback value: 1 (positive) or -1 (negative)")
    prompt: Optional[str] = Field(default=None, description="Original prompt")
    output: Optional[Dict[str, Any]] = Field(default=None, description="Output that was rated")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    
    @field_validator('feedback')
    @classmethod
    def validate_feedback(cls, v):
        if v not in [1, -1]:
            raise ValueError("feedback must be 1 (positive) or -1 (negative)")
        return v


class CoreFeedbackResponse(BaseModel):
    """Response schema for POST /core/feedback"""
    success: bool
    reward: int
    confidence_score: float
    rl_learning_active: bool = True


class CoreContextResponse(BaseModel):
    """Response schema for GET /core/context"""
    success: bool
    session_id: str
    entries: List[Dict[str, Any]]
    count: int


# ============================================================================
# MCP API Schemas
# ============================================================================

class SaveRuleRequest(BaseModel):
    """Request schema for POST /api/mcp/save_rule"""
    city: str
    rule_id: str   
    rule_text: str
    category: Optional[str] = None
    parsed_data: Optional[Dict[str, Any]] = None


class GeometryRequest(BaseModel):
    """Request schema for POST /api/mcp/geometry"""
    case_id: str
    geometry_data: Dict[str, Any]
    city: Optional[str] = None


class MCPFeedbackRequest(BaseModel):
    """Request schema for POST /api/mcp/feedback (legacy)"""
    case_id: str
    feedback: int  # -1 or 1
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# Health Endpoint Schema
# ============================================================================

class DependencyStatus(BaseModel):
    """Status of a dependency check."""
    status: str  # "ok" or "error"
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Response schema for GET /system/health"""
    status: str  # "healthy" or "degraded"
    core_bridge: bool
    feedback_store: bool
    tests_passed: bool
    integration_ready: bool
    dependencies: Dict[str, DependencyStatus]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
