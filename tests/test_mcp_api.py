# tests/test_mcp_api.py
"""
Tests for MCP API endpoints
"""
import pytest
import requests
from agents.agent_clients import (
    save_rule,
    list_rules,
    get_rules_for_city,
    send_feedback,
    log_geometry,
    save_output_summary,
    list_output_summaries,
)


class TestMCPConnectivity:
    """Test MCP server connectivity"""
    
    def test_mcp_server_running(self, mcp_base_url):
        """Test if MCP server is accessible"""
        try:
            # Remove /api/mcp from base_url to get root
            root_url = mcp_base_url.replace("/api/mcp", "")
            response = requests.get(root_url, timeout=5)
            assert response.status_code == 200, "MCP server should respond with 200"
            data = response.json()
            assert "message" in data or "endpoints" in data
        except requests.exceptions.RequestException as e:
            pytest.skip(f"MCP server not running: {e}")
    
    def test_mcp_endpoints_listed(self, mcp_base_url):
        """Test if MCP lists available endpoints"""
        try:
            root_url = mcp_base_url.replace("/api/mcp", "")
            response = requests.get(root_url, timeout=5)
            data = response.json()
            assert "endpoints" in data, "Should list available endpoints"
            endpoints = data["endpoints"]
            assert len(endpoints) >= 3, "Should have multiple endpoints"
        except requests.exceptions.RequestException:
            pytest.skip("MCP server not running")


class TestRulesAPI:
    """Test rules-related API endpoints"""
    
    def test_list_rules(self):
        """Test listing all rules"""
        rules = list_rules()
        assert isinstance(rules, list), "Should return a list"
        # Rules might be empty if DB is fresh, that's ok
    
    def test_get_rules_for_city(self, sample_cities):
        """Test getting rules for specific cities"""
        for city in sample_cities:
            rules = get_rules_for_city(city)
            assert isinstance(rules, list), f"Should return list for {city}"
            # Verify all returned rules are for the requested city
            for rule in rules:
                assert rule.get("city", "").lower() == city.lower(), \
                    f"All rules should be for {city}"
    
    def test_save_rule(self, sample_rule):
        """Test saving a new rule"""
        result = save_rule(sample_rule)
        if result is None:
            pytest.skip("MCP server not available")
        
        assert result.get("success") == True, "Should successfully save rule"
        assert "inserted_id" in result, "Should return inserted ID"
    
    def test_get_mumbai_rules(self):
        """Test specifically getting Mumbai rules"""
        mumbai_rules = get_rules_for_city("Mumbai")
        assert isinstance(mumbai_rules, list)
        if len(mumbai_rules) > 0:
            # Check structure of first rule
            rule = mumbai_rules[0]
            assert "city" in rule or "clause_no" in rule


class TestFeedbackAPI:
    """Test feedback and RL-related endpoints"""
    
    def test_send_positive_feedback(self):
        """Test sending thumbs up feedback"""
        result = send_feedback("test_case_001", "up")
        if result is None:
            pytest.skip("MCP server not available")
        
        assert result.get("success") == True
        assert result.get("reward") == 2, "Thumbs up should give +2 reward"
    
    def test_send_negative_feedback(self):
        """Test sending thumbs down feedback"""
        result = send_feedback("test_case_002", "down")
        if result is None:
            pytest.skip("MCP server not available")
        
        assert result.get("success") == True
        assert result.get("reward") == -2, "Thumbs down should give -2 reward"
    
    def test_invalid_feedback(self):
        """Test that invalid feedback values are handled"""
        result = send_feedback("test_case_003", "invalid")
        if result is None:
            pytest.skip("MCP server not available")
        
        # Should either reject or handle gracefully
        # Depends on server implementation


class TestGeometryAPI:
    """Test geometry logging endpoints"""
    
    def test_log_geometry(self):
        """Test logging geometry file reference"""
        result = log_geometry("test_case_geom_001", "outputs/geometry/test.glb")
        if result is None:
            pytest.skip("MCP server not available")
        
        assert result.get("success") == True
        assert result.get("case_id") == "test_case_geom_001"
        assert result.get("file") == "outputs/geometry/test.glb"
    
    def test_log_geometry_with_metadata(self):
        """Test logging geometry with additional metadata"""
        # This might need custom endpoint modification
        result = log_geometry("test_case_geom_002", "outputs/geometry/test2.glb")
        if result is None:
            pytest.skip("MCP server not available")
        
        assert result.get("success") == True

    def test_save_output_summary(self):
        """Ensure JSON output summaries can be stored."""
        result = save_output_summary(
            "TestCity",
            [{"clause_no": "1.1", "checks": {"height": {"ok": True}}}],
            "outputs/TestCity_calc_summary.json",
            case_id="TestCity_calc_summary",
        )
        if result is None:
            pytest.skip("MCP server not available")

        assert result.get("success") == True
        summaries = list_output_summaries("TestCity")
        assert isinstance(summaries, list)
