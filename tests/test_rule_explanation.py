import pytest
from utils.rule_explanation import format_rule_outcome


def test_format_rule_outcome_noncompliant():
    """Test non-compliant rule formatting."""
    outcome = {
        "clause_no": "116",
        "checks": {
            "height": {
                "subject": 21,
                "rule": {"op": "<=", "value_m": 15},
                "ok": False
            }
        }
    }
    explained = format_rule_outcome(outcome)
    
    assert "summary" in explained
    assert "explanation" in explained
    assert "technical" in explained
    assert "Non-compliant" in explained["summary"]
    assert len(explained["explanation"]) == 3
    assert "permissible building height is a maximum of 15 meters" in explained["explanation"][0]
    assert "21 meters" in explained["explanation"][1]
    assert "non-compliant" in explained["explanation"][2]


def test_format_rule_outcome_compliant():
    """Test compliant rule formatting."""
    outcome = {
        "clause_no": "117",
        "checks": {
            "height": {
                "subject": 12,
                "rule": {"op": "<=", "value_m": 15},
                "ok": True
            },
            "fsi": {
                "subject": 1.8,
                "rule": 2.0,
                "ok": True
            }
        }
    }
    explained = format_rule_outcome(outcome)
    
    assert "Compliant" in explained["summary"]
    assert "building height" in explained["summary"]
    assert "FSI" in explained["summary"]
    assert any("within the permissible limit" in line for line in explained["explanation"])


def test_format_rule_outcome_mixed_compliance():
    """Test mixed compliance formatting."""
    outcome = {
        "clause_no": "118",
        "checks": {
            "height": {
                "subject": 10,
                "rule": {"op": "<=", "value_m": 15},
                "ok": True
            },
            "fsi": {
                "subject": 2.5,
                "rule": 2.0,
                "ok": False
            }
        }
    }
    explained = format_rule_outcome(outcome)
    
    assert "Non-compliant" in explained["summary"]
    assert "FSI" in explained["summary"]
    assert "building height" in explained["summary"]
    assert len(explained["explanation"]) == 6  # 3 lines per check


def test_format_rule_outcome_no_data():
    """Test rule with insufficient data."""
    outcome = {
        "clause_no": "119",
        "checks": {
            "height": {
                "subject": None,
                "rule": {"op": "<=", "value_m": 15},
                "ok": None
            }
        }
    }
    explained = format_rule_outcome(outcome)
    
    assert "Insufficient data" in explained["summary"]
    assert "No proposed building height has been provided" in explained["explanation"][1]


def test_technical_preserved():
    """Ensure original JSON is preserved in technical field."""
    outcome = {
        "clause_no": "120",
        "checks": {
            "height": {
                "subject": 21,
                "rule": {"op": "<=", "value_m": 15},
                "ok": False
            }
        }
    }
    explained = format_rule_outcome(outcome)
    
    assert explained["technical"] == outcome
    assert explained["technical"]["checks"]["height"]["subject"] == 21
