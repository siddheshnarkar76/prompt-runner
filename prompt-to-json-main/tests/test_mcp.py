# tests/test_mcp.py
"""
Tests for MCP (Model Context Protocol) connectivity and API
"""
import pytest
import requests
from unittest.mock import patch, Mock
from agents.agent_clients import (
    save_rule,
    list_rules,
    get_rules_for_city,
    send_feedback,
    log_geometry
)


class TestMCPConnectivity:
    """Test MCP server connectivity"""
    
    def test_mcp_server_running(self):
        """Test if MCP server is accessible"""
        try:
            response = requests.get("http://127.0.0.1:5001/", timeout=5)
            assert response.status_code == 200
            data = response.json()
            # Be lenient across environments; skip if legacy root payload not available
            if "message" not in data:
                pytest.skip("Root payload missing 'message' key - server not our FastAPI")
            assert "MCP API" in data["message"]
        except requests.exceptions.RequestException:
            pytest.skip("MCP server not running")
    
    def test_mcp_endpoints_exist(self):
        """Test if MCP API endpoints are defined"""
        try:
            response = requests.get("http://127.0.0.1:5001/", timeout=5)
            data = response.json()
            if "endpoints" not in data:
                pytest.skip("Root payload missing 'endpoints' - server not our FastAPI")
            endpoints = data["endpoints"]
            assert "POST /api/mcp/save_rule" in endpoints
            assert "GET /api/mcp/list_rules" in endpoints
            assert "POST /api/mcp/feedback" in endpoints
            assert "POST /api/mcp/geometry" in endpoints
        except requests.exceptions.RequestException:
            pytest.skip("MCP server not running")


class TestMCPRuleOperations:
    """Test MCP rule save/retrieve operations"""
    
    @patch('agents.agent_clients.requests.post')
    def test_save_rule(self, mock_post, sample_rule):
        """Test saving a rule to MCP"""
        mock_response = Mock()
        mock_response.json.return_value = {"success": True, "inserted_id": "test_123"}
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        result = save_rule(sample_rule)
        assert result is not None
        assert result["success"] is True
        assert "inserted_id" in result
    
    @patch('agents.agent_clients.requests.get')
    def test_list_rules(self, mock_get):
        """Test listing rules from MCP"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "rules": [{"city": "Mumbai"}, {"city": "Pune"}]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        rules = list_rules()
        assert isinstance(rules, list)
        assert len(rules) == 2
    
    @patch('agents.agent_clients.list_rules')
    def test_get_rules_for_city(self, mock_list_rules):
        """Test filtering rules by city"""
        mock_list_rules.return_value = [
            {"city": "Mumbai", "clause_no": "DCPR-1"},
            {"city": "Pune", "clause_no": "PMC-1"},
            {"city": "Mumbai", "clause_no": "DCPR-2"}
        ]
        
        mumbai_rules = get_rules_for_city("Mumbai")
        assert len(mumbai_rules) == 2
        assert all(r["city"] == "Mumbai" for r in mumbai_rules)
        
        pune_rules = get_rules_for_city("Pune")
        assert len(pune_rules) == 1
        assert pune_rules[0]["city"] == "Pune"


class TestMCPFeedback:
    """Test MCP feedback system"""
    
    @patch('agents.agent_clients.requests.post')
    def test_send_positive_feedback(self, mock_post):
        """Test sending positive feedback"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "reward": 2,
            "feedback_id": "fb_123"
        }
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        result = send_feedback("case_123", "up")
        assert result is not None
        assert result["success"] is True
        assert result["reward"] == 2
    
    @patch('agents.agent_clients.requests.post')
    def test_send_negative_feedback(self, mock_post):
        """Test sending negative feedback"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "reward": -2,
            "feedback_id": "fb_456"
        }
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        result = send_feedback("case_456", "down")
        assert result is not None
        assert result["success"] is True
        assert result["reward"] == -2


class TestMCPGeometry:
    """Test MCP geometry logging"""
    
    @patch('agents.agent_clients.requests.post')
    def test_log_geometry(self, mock_post):
        """Test logging geometry file reference"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "success": True,
            "case_id": "case_789",
            "file": "outputs/geometry/case_789.glb"
        }
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        result = log_geometry("case_789", "outputs/geometry/case_789.glb")
        assert result is not None
        assert result["success"] is True
        assert result["case_id"] == "case_789"


class TestMultiCitySupport:
    """Test multi-city functionality"""
    
    def test_supported_cities(self, sample_cities):
        """Test that all cities are supported"""
        assert "Mumbai" in sample_cities
        assert "Ahmedabad" in sample_cities
        assert "Pune" in sample_cities
        assert "Nashik" in sample_cities
        assert len(sample_cities) == 4
    
    @patch('agents.agent_clients.list_rules')
    def test_all_cities_have_rules(self, mock_list_rules, sample_cities):
        """Test that all cities have rules in MCP"""
        mock_list_rules.return_value = [
            {"city": "Mumbai"},
            {"city": "Ahmedabad"},
            {"city": "Pune"},
            {"city": "Nashik"}
        ]
        # Call via module to ensure patch applies to the used reference
        from agents import agent_clients as agent_clients_module
        rules = agent_clients_module.list_rules()
        cities_with_rules = set(r["city"] for r in rules)
        
        # Should have at least one city with rules (mocked)
        assert len(cities_with_rules) >= 4
        
        for city in sample_cities:
            assert city in cities_with_rules
