import os
from unittest.mock import patch, MagicMock

# Ensure mongomock mode before importing mcp_server
os.environ["USE_MOCK_MONGO"] = "1"

from mcp_server import app  # noqa: E402


def _mock_bridge():
    class _B:
        def health_check(self):
            return {"bridge_connected": True}

    return _B()


def _fake_ping_mongo():
    return True, "ok"


def _fake_ping_noopur_disabled():
    return False, False, "disabled"


@patch("creatorcore_bridge.bridge_client.get_bridge", side_effect=_mock_bridge)
@patch("mcp_server._calculate_test_coverage", return_value=85)
@patch("mcp_server._ping_mongo", side_effect=_fake_ping_mongo)
@patch("mcp_server._ping_noopur", side_effect=_fake_ping_noopur_disabled)
def test_system_health_contract(mock_noopur, mock_mongo, mock_cov, mock_bridge):
    client = app.test_client()
    resp = client.get("/system/health")
    assert resp.status_code == 200
    data = resp.get_json()
    for key in [
        "status",
        "core_bridge",
        "feedback_store",
        "tests_passed",
        "integration_ready",
        "last_run",
        "dependencies",
    ]:
        assert key in data

    assert isinstance(data["core_bridge"], bool)
    assert isinstance(data["feedback_store"], bool)
    assert data["tests_passed"] == 85
    assert isinstance(data["integration_ready"], bool)
    deps = data["dependencies"]
    assert "mongo" in deps and "noopur" in deps
    assert deps["mongo"]["ok"] is True
    assert deps["noopur"]["enabled"] is False


def test_core_feedback_validation_rejects_bad_payload():
    client = app.test_client()
    resp = client.post("/core/feedback", json={"case_id": "abc", "feedback": "up"})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["success"] is False
    assert any("feedback" in e for e in body.get("errors", []))


def test_core_context_validation_limit_bounds():
    client = app.test_client()
    resp = client.get("/core/context?user_id=abc&limit=0")
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["success"] is False
    assert any("limit" in e for e in body.get("errors", []))
