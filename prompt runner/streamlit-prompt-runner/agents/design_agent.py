# agents/design_agent.py
"""
Design Agent (Fixed)
Converts user prompt to normalized building specification.
Delegates to compliance_pipeline for full processing.
"""
import logging
import re
from typing import Dict, Any
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def prompt_to_spec(prompt: str) -> Dict[str, Any]:
    """
    Convert prompt to normalized building specification.
    Uses compliance_pipeline for full processing.
    """
    from agents.compliance_pipeline import run_compliance_pipeline, normalize_spec
    
    # For now, just normalize the spec
    # Full pipeline will be called by main.py
    spec = normalize_spec(prompt)
    
    # Add schema for backward compatibility
    spec.update({
        "type": "building_specification",
        "building_type": spec.get("building_type", "residential"),
        "description": prompt,
        "meta": {
            "generated_by": "design_agent_v3",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "confidence": 0.9
        }
    })
    
    logger.info(f"Normalized spec for prompt: case_id={spec['case_id']}, city={spec['city']}")
    return spec
