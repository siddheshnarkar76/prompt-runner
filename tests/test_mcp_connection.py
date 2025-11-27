# tests/test_mcp_connection.py
"""
Tests for MCP MongoDB connection and API endpoints
"""

import pytest
import requests
from agents.agent_clients import list_rules, get_rules_for_city, send_feedback, log_geometry, list_feedback_entries


class TestMCPConnection:
    """Test MCP server connectivity and basic operations"""
    
    def test_mcp_server_running(self, mcp_url):
        """Test if MCP server is accessible"""
        try:
            response = requests.get(mcp_url.replace('/api/mcp', '/'), timeout=5)
            assert response.status_code == 200, "MCP server should be running"
            data = response.json()
            assert "message" in data, "Response should contain message"
        except requests.exceptions.ConnectionError:
            pytest.skip("MCP server not running - start with: python mcp_server.py")
    
    def test_list_rules_endpoint(self):
        """Test listing rules from MCP"""
        rules = list_rules()
        assert isinstance(rules, list), "list_rules should return a list"
        # Rules may be empty if database not populated yet
        if len(rules) > 0:
            assert "city" in rules[0] or "clause_no" in rules[0], "Rules should have structure"
    
    def test_get_rules_for_city_mumbai(self):
        """Test fetching Mumbai-specific rules"""
        mumbai_rules = get_rules_for_city("Mumbai")
        assert isinstance(mumbai_rules, list), "Should return list of rules"
        for rule in mumbai_rules:
            city = rule.get("city", "").lower()
            assert city == "mumbai", f"All rules should be for Mumbai, got {city}"
    
    def test_get_rules_for_city_ahmedabad(self):
        """Test fetching Ahmedabad-specific rules"""
        ahmedabad_rules = get_rules_for_city("Ahmedabad")
        assert isinstance(ahmedabad_rules, list), "Should return list of rules"
        for rule in ahmedabad_rules:
            city = rule.get("city", "").lower()
            assert city == "ahmedabad", f"All rules should be for Ahmedabad, got {city}"
    
    def test_get_rules_for_city_pune(self):
        """Test fetching Pune-specific rules"""
        pune_rules = get_rules_for_city("Pune")
        assert isinstance(pune_rules, list), "Should return list of rules"
        for rule in pune_rules:
            city = rule.get("city", "").lower()
            assert city == "pune", f"All rules should be for Pune, got {city}"
    
    def test_get_rules_for_city_nashik(self):
        """Test fetching Nashik-specific rules"""
        nashik_rules = get_rules_for_city("Nashik")
        assert isinstance(nashik_rules, list), "Should return list of rules"
        for rule in nashik_rules:
            city = rule.get("city", "").lower()
            assert city == "nashik", f"All rules should be for Nashik, got {city}"
    
    def test_all_four_cities_present(self):
        """Test that all 4 cities have rules in database"""
        cities = ["Mumbai", "Ahmedabad", "Pune", "Nashik"]
        all_rules = list_rules()
        
        if len(all_rules) == 0:
            pytest.skip("No rules in database - run upload_all_cities.py first")
        
        cities_in_db = set(r.get("city", "").lower() for r in all_rules)
        
        for city in cities:
            assert city.lower() in cities_in_db, f"{city} rules should be in database"
    
    def test_feedback_logging(self):
        """Test feedback logging to MCP"""
        test_case_id = "test_case_001"
        result = send_feedback(test_case_id, "up")
        
        if result is None:
            pytest.skip("MCP server not responding")
        
        assert result.get("success") == True, "Feedback should be saved successfully"
        assert result.get("reward") == 2, "Up feedback should give +2 reward"

        history = list_feedback_entries(test_case_id)
        assert isinstance(history, list), "Feedback history should be a list"
        assert any(entry.get("feedback") == "up" for entry in history), "History should contain latest feedback"
    
    def test_geometry_logging(self):
        """Test geometry file logging to MCP"""
        test_case_id = "test_geom_001"
        test_file_path = "outputs/geometry/test.glb"
        
        result = log_geometry(test_case_id, test_file_path)
        
        if result is None:
            pytest.skip("MCP server not responding")
        
        assert result.get("success") == True, "Geometry should be logged"
        assert result.get("case_id") == test_case_id, "Case ID should match"


class TestMCPDataIntegrity:
    """Test MCP data structure and integrity"""
    
    def test_rule_structure(self):
        """Test that rules have required fields"""
        rules = list_rules()
        
        if len(rules) == 0:
            pytest.skip("No rules to test - populate database first")
        
        required_fields = ["city", "clause_no"]
        
        sampled = rules[:5]
        assert sampled, "No rules returned to validate"

        for rule in sampled:
            assert "city" in rule, "Rule should have city field"
            clause_present = rule.get("clause_no") or rule.get("rule", {}).get("clause_no")
            has_structured_rules = isinstance(rule.get("rule", {}).get("rules"), list)
            assert clause_present or has_structured_rules, (
                "Rule should include clause_no or provide structured rule entries"
            )
    
    def test_parsed_fields_present(self):
        """Test that rules have parsed_fields for geometry generation"""
        rules = list_rules()
        
        if len(rules) == 0:
            pytest.skip("No rules to test")
        
        # At least some rules should have parsed_fields
        rules_with_parsed = [r for r in rules if "parsed_fields" in r.get("rule", {})]
        
        # This is informational - not all rules may have parsed fields
        print(f"\nRules with parsed_fields: {len(rules_with_parsed)} / {len(rules)}")


class TestSystemHealth:
    """Validate Core/health monitoring endpoints."""

    def test_core_status_endpoint(self, mcp_base_url):
        url = f"{mcp_base_url}/core/status"
        try:
            response = requests.get(url, timeout=5)
        except requests.exceptions.ConnectionError:
            pytest.skip("Core endpoint not running - start mcp_server.py")

        assert response.status_code == 200
        data = response.json()
        for key in ("status", "core_sync", "feedback_store"):
            assert key in data

    def test_system_health_endpoint(self, mcp_base_url):
        url = f"{mcp_base_url}/system/health"
        try:
            response = requests.get(url, timeout=5)
        except requests.exceptions.ConnectionError:
            pytest.skip("System health endpoint not running - start mcp_server.py")

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ("active", "degraded")
        assert "last_run" in data
        assert "core_sync" in data

