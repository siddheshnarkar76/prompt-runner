"""
Unified Compliance Pipeline (PRODUCTION)
Production-ready pipeline with deterministic outputs and full traceability.

EXECUTION ORDER (STRICT):
1. Normalize Spec (prompt → clean JSON)
2. Validate (check required fields)
3. Filter Rules (only applicable rules)
4. Evaluate Rules (no duplicates, no NULLs)
5. Generate Geometry (if dimensions exist)
6. Summarize Output (traceable by case_id + trace_id)
"""
import logging
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global trace ID for current execution (set at pipeline start)
_CURRENT_TRACE_ID = None

def generate_trace_id() -> str:
    """Generate unique trace ID for entire pipeline execution."""
    return str(uuid.uuid4())

def get_trace_id() -> str:
    """Get current trace ID or generate new one."""
    global _CURRENT_TRACE_ID
    if _CURRENT_TRACE_ID is None:
        _CURRENT_TRACE_ID = generate_trace_id()
    return _CURRENT_TRACE_ID

def set_trace_id(trace_id: str):
    """Set trace ID for current execution (for external orchestration)."""
    global _CURRENT_TRACE_ID
    _CURRENT_TRACE_ID = trace_id


# ============================================================================
# STEP 1: NORMALIZE SPEC (Prompt → Domain Spec)
# ============================================================================

def normalize_spec(prompt: str, city: str = None, run_id: str = None) -> Dict[str, Any]:
    """
    Convert user prompt to canonical planning spec.
    All planning fields default to None; UI-provided overrides will fill them.
    
    Args:
        prompt: User input prompt
        city: Target city (optional, will be detected)
        run_id: Optional run identifier (generated if not provided)
    """
    import re

    case_id = run_id if run_id else str(uuid.uuid4())[:8]
    trace_id = get_trace_id()
    prompt_lower = prompt.lower()

    # Fallback city detection (UI should provide explicitly)
    if not city:
        if "mumbai" in prompt_lower:
            city = "Mumbai"
        elif "pune" in prompt_lower:
            city = "Pune"
        elif "nashik" in prompt_lower:
            city = "Nashik"
        elif "ahmedabad" in prompt_lower:
            city = "Ahmedabad"
        else:
            city = "Mumbai"

    def extract_number(pattern: str) -> Optional[float]:
        match = re.search(pattern, prompt_lower)
        if match:
            try:
                return float(match.group(1))
            except Exception:
                return None
        return None

    spec = {
        "case_id": case_id,
        "trace_id": trace_id,
        "run_id": case_id,  # run_id = case_id for this execution
        "city": city,
        "land_use_zone": None,
        "plot_area_sq_m": None,
        "plot_width_m": None,
        "plot_frontage_m": None,
        "abutting_road_width_m": None,
        "building_use": None,
        "building_type": None,
        "is_core_area": None,
        "height_m": extract_number(r"(\d+(?:\.\d+)?)\s*(?:m|meter|metre)\s*(?:height|tall)?"),
        "fsi": extract_number(r"fsi\s*(\d+(?:\.\d+)?)"),
        "setback_m": extract_number(r"setback\s*(\d+(?:\.\d+)?)"),
        # Geometry helpers; mapped later from plot dims if available
        "width_m": None,
        "depth_m": None,
    }

    logger.info("Normalized spec: case_id=%s, city=%s", case_id, city)
    return spec


# ============================================================================
# STEP 2: VALIDATE (Check Required Fields)
# ============================================================================

MANDATORY_PLANNING_FIELDS = [
    "land_use_zone",
    "plot_area_sq_m",
    "abutting_road_width_m",
    "building_use",
]


def validate_spec(spec: Dict[str, Any]) -> Tuple[bool, Optional[List[str]]]:
    """
    Validate spec has mandatory planning context fields populated.
    """
    missing = []
    for field in MANDATORY_PLANNING_FIELDS:
        if spec.get(field) is None:
            missing.append(field)

    if missing:
        logger.warning("Validation failed: missing planning fields: %s", missing)
        return False, missing

    logger.info("Validation passed for case_id=%s", spec.get("case_id"))
    return True, None


def blocked_response(spec: Dict[str, Any], missing_fields: List[str]) -> Dict[str, Any]:
    """
    Return BLOCKED response when validation fails.
    Does NOT run any rules.
    """
    return {
        "status": "BLOCKED",
        "case_id": spec.get("case_id", "unknown"),
        "trace_id": spec.get("trace_id", get_trace_id()),
        "run_id": spec.get("run_id", spec.get("case_id", "unknown")),
        "reason": "Missing mandatory planning parameters required by DCPR",
        "missing_fields": missing_fields,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


# ============================================================================
# STEP 3: FILTER RULES (Only Applicable Rules, No Duplicates)
# ============================================================================

def filter_applicable_rules(
    rules: List[Dict[str, Any]],
    spec: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Filter rules to only those applicable to spec.
    Remove duplicates (same clause_no).
    Target: 5-8 rules, not 40+.
    
    Each rule must define:
    - clause_no: unique identifier
    - required_fields: list of fields needed in spec
    - category: height/fsi/setback/etc.
    """
    def conditions_match(conditions: Dict[str, Any], subject: Dict[str, Any]) -> bool:
        if not conditions:
            return True
        for field, cond in conditions.items():
            val = subject.get(field)
            if val is None:
                return False
            if isinstance(cond, list):
                if val not in cond:
                    return False
            elif isinstance(cond, dict):
                min_v = cond.get("min")
                max_v = cond.get("max")
                eq_v = cond.get("equals")
                if min_v is not None and float(val) < float(min_v):
                    return False
                if max_v is not None and float(val) > float(max_v):
                    return False
                if eq_v is not None and val != eq_v:
                    return False
            else:
                if val != cond:
                    return False
        return True

    applicable = []
    seen_clauses = set()

    for rule in rules:
        clause_no = rule.get("clause_no") or rule.get("id")

        # City match
        rule_city = (rule.get("city") or spec.get("city") or "").lower()
        if rule_city and rule_city != (spec.get("city") or "").lower():
            continue

        # Skip duplicates
        if clause_no in seen_clauses:
            continue

        required_fields = rule.get("required_fields") or []
        if not required_fields:
            # Without explicit required fields, skip to avoid false positives
            continue

        # Ensure all required fields are present and non-null
        if not all(spec.get(f) is not None for f in required_fields):
            continue

        # Evaluate conditions
        if not conditions_match(rule.get("conditions", {}), spec):
            continue

        applicable.append(rule)
        seen_clauses.add(clause_no)

    logger.info("Filtered %s rules → %s applicable", len(rules), len(applicable))
    return applicable


# ============================================================================
# STEP 4: EVALUATE RULES (No NULLs, Clean Output)
# ============================================================================

def evaluate_single_rule(
    rule: Dict[str, Any],
    spec: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluate ONE rule against spec.
    Returns clean dict with NO NULL values.
    
    Example output:
    {
        "clause_no": "6",
        "category": "height",
        "checks": {
            "height": {
                "rule_max": 15,
                "subject": 8,
                "ok": true
            }
        }
    }
    """
    clause_no = rule.get("clause_no") or rule.get("id") or "unknown"
    limits = rule.get("limits", {})
    checks: Dict[str, Any] = {}

    for field, limit in limits.items():
        subject = spec.get(field)
        if subject is None:
            continue

        # Numeric limits
        if isinstance(limit, dict):
            rule_min = limit.get("min")
            rule_max = limit.get("max")
            ok_parts = []
            if rule_min is not None:
                ok_parts.append(float(subject) >= float(rule_min))
            if rule_max is not None:
                ok_parts.append(float(subject) <= float(rule_max))
            ok = all(ok_parts) if ok_parts else True
            checks[field] = {
                "rule_min": float(rule_min) if rule_min is not None else None,
                "rule_max": float(rule_max) if rule_max is not None else None,
                "subject": float(subject),
                "ok": ok
            }
        else:
            # Simple max limit
            ok = float(subject) <= float(limit)
            checks[field] = {
                "rule_max": float(limit),
                "subject": float(subject),
                "ok": ok
            }

    # Remove nulls from checks entries
    for field, data in list(checks.items()):
        cleaned = {k: v for k, v in data.items() if v is not None}
        cleaned.setdefault("ok", True)
        checks[field] = cleaned

    if not checks:
        logger.debug("Rule %s has no evaluable limits", clause_no)

    return {
        "clause_no": str(clause_no),
        "checks": checks,
        "evaluated_at": datetime.utcnow().isoformat() + "Z"
    }


def evaluate_all_rules(
    rules: List[Dict[str, Any]],
    spec: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Evaluate all applicable rules.
    Returns list of clean evaluation results (NO NULLs).
    """
    results = []
    
    for rule in rules:
        try:
            result = evaluate_single_rule(rule, spec)
            results.append(result)
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.get('clause_no')}: {e}")
            # Don't include failed rules
            continue
    
    logger.info(f"Evaluated {len(results)} rules successfully")
    return results


# ============================================================================
# STEP 5: GENERATE GEOMETRY
# ============================================================================

def generate_geometry(spec: Dict[str, Any]) -> Optional[str]:
    """
    Generate .glb geometry if dimensions exist.
    Save to /reports/geometry_outputs/{case_id}.glb
    
    Returns:
        Path to .glb file, or None if generation failed
    """
    try:
        from utils.geometry_converter import json_to_glb
        import trimesh
        
        case_id = spec.get("case_id")
        height_m = spec.get("height_m") or 20.0  # Default to 20m
        width_m = spec.get("width_m") or 30.0    # Default to 30m
        depth_m = spec.get("depth_m") or 20.0    # Default to 20m
        
        # Use defaults if dimensions are missing
        if not case_id:
            logger.warning(f"Cannot generate geometry: missing case_id")
            return None
        
        # Create spec for geometry generation
        geom_spec = {
            "parameters": {
                "height_m": float(height_m),
                "width_m": float(width_m),
                "depth_m": float(depth_m),
                "setback_m": float(spec.get("setback_m") or 3.0),
                "type": spec.get("building_type", "residential")
            }
        }
        
        # Generate GLB
        output_dir = Path("data/outputs/geometry")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        glb_path = output_dir / f"{case_id}.glb"
        
        try:
            # Try using json_to_glb first
            json_to_glb(
                json_path=f"{case_id}.json",
                output_dir=str(output_dir),
                spec_data=geom_spec
            )
            
            if glb_path.exists():
                logger.info(f"✅ Generated geometry: {glb_path}")
                return str(glb_path)
        except Exception as e:
            logger.debug(f"json_to_glb failed, using trimesh directly: {e}")
        
        # Fallback: create simple box geometry with trimesh
        try:
            box = trimesh.creation.box(
                extents=[float(width_m), float(depth_m), float(height_m)]
            )
            box.export(str(glb_path))
            
            logger.info(f"✅ Generated geometry (trimesh fallback): {glb_path}")
            return str(glb_path)
        except Exception as e2:
            logger.error(f"Trimesh geometry generation failed: {e2}")
            return None
        
    except Exception as e:
        logger.error(f"Geometry generation error: {e}")
        return None


# ============================================================================
# STEP 6: SUMMARIZE OUTPUT (Traceable)
# ============================================================================

def summarize_compliance(
    spec: Dict[str, Any],
    evaluations: List[Dict[str, Any]],
    geometry_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create final, traceable output.
    All data linked by case_id.
    """
    case_id = spec.get("case_id")
    city = spec.get("city")
    
    # Calculate overall compliance
    all_ok = True
    compliant_count = 0
    non_compliant_count = 0
    
    for eval_result in evaluations:
        checks = eval_result.get("checks", {})
        for check_key, check_data in checks.items():
            if check_key == "status":
                continue
            if isinstance(check_data, dict) and "ok" in check_data:
                if check_data["ok"]:
                    compliant_count += 1
                else:
                    non_compliant_count += 1
                    all_ok = False
    
    overall_status = "COMPLIANT" if all_ok and compliant_count > 0 else "NON_COMPLIANT" if non_compliant_count > 0 else "INCOMPLETE"
    
    summary = {
        "case_id": case_id,
        "trace_id": spec.get("trace_id", get_trace_id()),
        "run_id": spec.get("run_id", case_id),
        "city": city,
        "status": overall_status,
        "summary": {
            "total_rules_evaluated": len(evaluations),
            "compliant_checks": compliant_count,
            "non_compliant_checks": non_compliant_count,
            "compliance_rate": round(compliant_count / (compliant_count + non_compliant_count) * 100, 1) if (compliant_count + non_compliant_count) > 0 else 0
        },
        "building_parameters": {
            "city": spec.get("city"),
            "land_use_zone": spec.get("land_use_zone"),
            "plot_area_sq_m": spec.get("plot_area_sq_m"),
            "plot_width_m": spec.get("plot_width_m"),
            "plot_frontage_m": spec.get("plot_frontage_m"),
            "abutting_road_width_m": spec.get("abutting_road_width_m"),
            "building_use": spec.get("building_use"),
            "building_type": spec.get("building_type"),
            "is_core_area": spec.get("is_core_area"),
            "height_m": spec.get("height_m"),
            "fsi": spec.get("fsi"),
            "setback_m": spec.get("setback_m")
        },
        "evaluations": evaluations,
        "geometry": {
            "generated": geometry_path is not None,
            "path": geometry_path
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    logger.info(f"Summary: case_id={case_id}, status={overall_status}, compliant={compliant_count}, non_compliant={non_compliant_count}")
    return summary


# ============================================================================
# MAIN PIPELINE (ORCHESTRATOR)
# ============================================================================

def run_compliance_pipeline(
    prompt: str,
    city: str = None,
    rules: List[Dict[str, Any]] = None,
    spec_override: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    FULL EXECUTION FLOW (STRICT ORDER):
    
    1. Normalize Spec
    2. Validate
    3. Filter Rules
    4. Evaluate Rules
    5. Generate Geometry
    6. Summarize
    
    Args:
        prompt: User input
        city: Target city
        rules: List of DCR rules
        spec_override: Override normalized spec fields
        trace_id: Optional trace ID for distributed tracing
    
    Returns:
        Clean, traceable output with no NULLs, includes trace_id
    """
    
    # Set trace ID for this pipeline run
    if trace_id:
        set_trace_id(trace_id)
    else:
        set_trace_id(generate_trace_id())
    # STEP 1: Normalize
    logger.info("STEP 1: Normalizing spec...")
    spec = normalize_spec(prompt, city)
    if spec_override:
        spec.update({k: v for k, v in spec_override.items()})

    # Map geometry helper fields from plot dims when present
    if spec.get("plot_width_m") is not None:
        spec["width_m"] = spec.get("plot_width_m")
    if spec.get("plot_frontage_m") is not None:
        spec["depth_m"] = spec.get("plot_frontage_m")
    
    # STEP 2: Validate
    logger.info("STEP 2: Validating spec...")
    is_valid, missing = validate_spec(spec)
    if not is_valid:
        logger.error(f"Validation blocked: {missing}")
        return blocked_response(spec, missing)
    
    # STEP 3: Filter Rules
    logger.info("STEP 3: Filtering rules...")
    if not rules:
        rules = []
    applicable_rules = filter_applicable_rules(rules, spec)
    
    if not applicable_rules:
        logger.warning(f"No applicable rules found for {spec['city']}")
        return {
            "status": "ERROR",
            "case_id": spec.get("case_id"),
            "trace_id": spec.get("trace_id", get_trace_id()),
            "run_id": spec.get("run_id", spec.get("case_id")),
            "city": spec.get("city"),
            "reason": "No applicable DCPR rules matched. Check rule schema or inputs.",
            "evaluations": [],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    # STEP 4: Evaluate Rules
    logger.info("STEP 4: Evaluating rules...")
    evaluations = evaluate_all_rules(applicable_rules, spec)
    
    # STEP 5: Generate Geometry
    logger.info("STEP 5: Generating geometry...")
    geometry_path = generate_geometry(spec)
    
    # STEP 6: Summarize
    logger.info("STEP 6: Summarizing output...")
    summary = summarize_compliance(spec, evaluations, geometry_path)
    
    logger.info(f"✅ Pipeline complete: case_id={spec['case_id']}")
    return summary
