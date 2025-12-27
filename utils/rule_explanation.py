from typing import Dict, Any, List, Optional

LEGAL_AUTHORITY_DEFAULT = "DCPR 2034"

# Optional templates per clause. Can be extended over time.
CLAUSE_TEMPLATES: Dict[str, str] = {
    # Example mappings; fallback will handle anything not listed.
    # "116": "maximum permissible building height is {allowed} meters",
}


def _format_allowed_for_height(rule: Dict[str, Any]) -> Optional[str]:
    """Derive a human-readable allowed statement from a parsed height rule.
    Expects keys like op and value_m.
    """
    if not isinstance(rule, dict):
        return None
    op = rule.get("op")
    val = rule.get("value_m")
    if val is None:
        return None
    if op in ("<=", "<"):
        return f"a maximum of {val} meters"
    if op in (">=", ">"):
        return f"a minimum of {val} meters"
    if op in ("=",):
        return f"exactly {val} meters"
    # Generic fallback
    return f"{op or 'constraint'} {val} meters"


def _format_allowed_for_fsi(rule: Any) -> Optional[str]:
    try:
        val = float(rule)
        return f"an FSI not exceeding {val}"
    except Exception:
        return None


def _check_label(check_key: str) -> str:
    return {
        "height": "building height",
        "fsi": "FSI",
        "setback": "setback",
        "width": "building width",
        "depth": "building depth",
    }.get(check_key, check_key.replace("_", " "))


def _allowed_phrase(check_key: str, rule: Any) -> Optional[str]:
    if check_key == "height":
        return _format_allowed_for_height(rule)
    if check_key == "fsi":
        return _format_allowed_for_fsi(rule)
    # Generic fallback if we don't have a specific formatter
    if rule is None:
        return None
    try:
        return str(rule)
    except Exception:
        return None


def _compliance_phrase(ok: Optional[bool]) -> str:
    if ok is True:
        return "compliant"
    if ok is False:
        return "non-compliant"
    return "insufficient data to assess"


def format_rule_outcome(outcome: Dict[str, Any], *, authority: str = LEGAL_AUTHORITY_DEFAULT) -> Dict[str, Any]:
    """
    Convert a single rule-evaluation JSON into a legally-worded, human-readable structure.

    Returns dict with keys: summary (str), explanation (List[str]), technical (original outcome)
    """
    clause_no = outcome.get("clause_no") or "N/A"
    checks: Dict[str, Dict[str, Any]] = outcome.get("checks", {})

    # Build explanation lines per check
    explanation: List[str] = []
    failing: List[str] = []
    passing: List[str] = []
    unknown: List[str] = []

    for check_key, detail in checks.items():
        ok = detail.get("ok")
        subject = detail.get("subject")
        rule = detail.get("rule")
        label = _check_label(check_key)

        allowed_phrase = _allowed_phrase(check_key, rule)

        # Line 1: Rule statement
        if allowed_phrase:
            explanation.append(
                f"As per {authority}, Clause {clause_no}, the permissible {label} is {allowed_phrase}."
            )
        else:
            explanation.append(
                f"As per {authority}, Clause {clause_no}, constraints apply to {label}."
            )

        # Line 2: Proposed value comparison
        if subject is not None:
            # Units for common parameters
            unit = "meters" if check_key in {"height", "setback", "width", "depth"} else ""
            unit_str = f" {unit}" if unit else ""

            # Qualify relation using ok without re-evaluating
            if ok is True:
                relation = "which is within the permissible limit"
            elif ok is False:
                relation = "which exceeds the permissible limit"
            else:
                relation = "however, the data is insufficient to establish compliance"

            explanation.append(
                f"The proposed {label} is {subject}{unit_str}, {relation}."
            )
        else:
            explanation.append(
                f"No proposed {label} has been provided; assessment cannot be completed for this parameter."
            )

        # Line 3: Compliance conclusion for the parameter
        status_phrase = _compliance_phrase(ok)
        explanation.append(
            f"Therefore, with respect to {label}, the proposal is {status_phrase} under Clause {clause_no}."
        )

        # Track for overall summary
        if ok is True:
            passing.append(label)
        elif ok is False:
            failing.append(label)
        else:
            unknown.append(label)

    # Overall summary string
    if failing:
        summary = (
            f"Overall assessment: Non-compliant with Clause {clause_no} for "
            f"{', '.join(failing)};"
        )
        if passing:
            summary += f" compliant for {', '.join(passing)}."
        else:
            summary += " no parameters found compliant."
        if unknown:
            summary += f" Assessment pending data for {', '.join(unknown)}."
    elif passing:
        summary = (
            f"Overall assessment: Compliant with Clause {clause_no} for "
            f"{', '.join(passing)}."
        )
        if unknown:
            summary += f" Assessment pending data for {', '.join(unknown)}."
    else:
        summary = (
            f"Overall assessment: Insufficient data to assess compliance under Clause {clause_no}."
        )

    return {
        "summary": summary,
        "explanation": explanation,
        "technical": outcome,
    }


def format_rule_outcomes(outcomes: List[Dict[str, Any]], *, authority: str = LEGAL_AUTHORITY_DEFAULT) -> List[Dict[str, Any]]:
    """Batch format helper."""
    return [format_rule_outcome(o, authority=authority) for o in outcomes]
