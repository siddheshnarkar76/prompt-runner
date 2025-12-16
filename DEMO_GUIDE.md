# CreatorCore Integration Demo Guide

## Overview

This guide demonstrates the CreatorCore integration features implemented in the Streamlit Prompt Runner system.

## Prerequisites

1. **MongoDB** running (local or Atlas)
2. **Python 3.8+** installed
3. **Dependencies** installed: `pip install -r requirements.txt`

## Quick Start

### Step 1: Start the MCP Server

```bash
cd streamlit-prompt-runner
python mcp_server.py
```

The server will start on `http://localhost:5001`

### Step 2: Start the Streamlit App (Optional)

In a new terminal:

```bash
cd streamlit-prompt-runner
streamlit run main.py
```

## Demo Scenarios

### Scenario 1: Testing Bridge Connectivity

**Objective**: Verify that the CreatorCore bridge client can connect and communicate with the MCP server.

**Steps**:

1. Ensure MCP server is running
2. Run the bridge connectivity tests:

```bash
python -m pytest tests/test_bridge_connectivity.py -v
```

**Expected Output**:
```
test_bridge_initialization PASSED
test_send_log_success PASSED
test_send_feedback_success PASSED
test_get_context_success PASSED
test_health_check_success PASSED
...
```

### Scenario 2: Testing Feedback Flow

**Objective**: Verify that feedback submissions work end-to-end.

**Steps**:

1. Ensure MCP server is running
2. Run the feedback flow test:

```bash
python test_feedback_flow.py
```

**Expected Output**:
```
Testing CreatorCore Feedback Integration...

Test Case 1: mumbai_test_001 - up (Mumbai)
  ✓ Success: reward=2, core_success=True

Test Case 2: pune_test_001 - down (Pune)
  ✓ Success: reward=-2, core_success=True

Test Case 3: mumbai_test_001 - up (Mumbai)
  ✓ Success: reward=2, core_success=True

Testing Cumulative Scoring...
  mumbai_test_001: confidence=0.67, count=2
  pune_test_001: confidence=-1.0, count=1

Test Results:
  Total Tests: 3
  Successful: 3
  Success Rate: 100.0%
  Status: PASS
```

### Scenario 3: Testing Health Endpoint

**Objective**: Verify the health monitoring system.

**Steps**:

1. Ensure MCP server is running
2. Check health endpoint:

```bash
curl http://localhost:5001/system/health
```

**Expected Output**:
```json
{
  "status": "active",
  "core_bridge": true,
  "feedback_store": true,
  "last_run": "2025-12-02T12:00:00Z",
  "tests_passed": 90
}
```

### Scenario 4: Testing Log Submission

**Objective**: Verify that logs are properly submitted to CreatorCore.

**Steps**:

1. Use Python to submit a log:

```python
from creatorcore_bridge.bridge_client import get_bridge

bridge = get_bridge()
response = bridge.send_log(
    case_id="demo_case_001",
    prompt="Generate building specification for Mumbai",
    output={"city": "Mumbai", "buildings": [{"type": "residential", "floors": 10}]},
    metadata={"city": "Mumbai", "model": "gpt-4"}
)

print(response)
```

**Expected Output**:
```json
{
  "success": true,
  "log_id": "507f1f77bcf86cd799439011"
}
```

### Scenario 5: Testing Context Retrieval

**Objective**: Verify that user context can be retrieved for prompt warming.

**Steps**:

1. First, submit some logs (see Scenario 4)
2. Retrieve context:

```python
from creatorcore_bridge.bridge_client import get_bridge

bridge = get_bridge()
context = bridge.get_context(user_id="demo_case_001", limit=3)

print(context)
```

**Expected Output**:
```json
{
  "success": true,
  "context": [
    {
      "case_id": "demo_case_001",
      "prompt": "Generate building specification for Mumbai",
      "output": {"city": "Mumbai", "buildings": [...]},
      "timestamp": "2025-12-02T12:00:00Z"
    }
  ],
  "count": 1
}
```

### Scenario 6: End-to-End Workflow

**Objective**: Demonstrate the complete workflow from prompt to feedback.

**Steps**:

1. **Submit a prompt** (via Streamlit UI or API):
   - Open `http://localhost:8501` (if Streamlit is running)
   - Enter a prompt: "Generate building specification for Mumbai"
   - Click "Generate"

2. **Review the output**:
   - View the generated JSON specification
   - Check the case_id

3. **Submit feedback**:
   - Click "👍 Good result" or "👎 Needs improvement"
   - Verify feedback is saved

4. **Check feedback history**:
```python
from agents.rl_agent import get_feedback_before_next_run

summary = get_feedback_before_next_run("your_case_id")
print(f"Confidence: {summary['confidence_score']}")
print(f"Feedback Count: {summary['feedback_count']}")
```

## API Testing with cURL

### Test Log Endpoint

```bash
curl -X POST http://localhost:5001/core/log \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "curl_test_001",
    "event": "prompt_processed",
    "prompt": "Test prompt",
    "output": {"result": "test"},
    "timestamp": "2025-12-02T12:00:00Z"
  }'
```

### Test Feedback Endpoint

```bash
curl -X POST http://localhost:5001/core/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "curl_test_001",
    "feedback": 1,
    "timestamp": "2025-12-02T12:00:00Z"
  }'
```

### Test Context Endpoint

```bash
curl "http://localhost:5001/core/context?user_id=curl_test_001&limit=3"
```

### Test Health Endpoint

```bash
curl http://localhost:5001/system/health
```

## Running Full Test Suite

To run all CreatorCore-related tests:

```bash
# Run all CreatorCore tests
python -m pytest tests/test_creatorcore_* tests/test_bridge_connectivity.py -v

# Run with coverage
python -m pytest tests/test_creatorcore_* tests/test_bridge_connectivity.py --cov=creatorcore_bridge --cov=agents --cov-report=html
```

## Verification Checklist

- [ ] MCP server starts without errors
- [ ] Health endpoint returns `status: "active"`
- [ ] Bridge connectivity test passes
- [ ] Log submission returns `success: true`
- [ ] Feedback submission returns `success: true` and proper reward
- [ ] Context retrieval returns recent interactions
- [ ] Feedback flow test shows 100% success rate
- [ ] Test coverage is ≥90%

## Troubleshooting

### Issue: Bridge connectivity fails

**Solution**: 
- Ensure MCP server is running on `http://localhost:5001`
- Check `CREATORCORE_BASE_URL` environment variable
- Verify network connectivity

### Issue: Feedback returns success: false

**Solution**:
- Check MongoDB connection
- Verify `creator_feedback` collection exists
- Check server logs for errors

### Issue: Test coverage below 90%

**Solution**:
- Run all tests: `pytest tests/ -v`
- Fix any failing tests
- Ensure MCP server is running for integration tests

## Next Steps

1. **Integration with CreatorCore**: Coordinate with Aman Pal for endpoint contract finalization
2. **Context Memory**: Sync with Noopur for context memory integration
3. **QA Validation**: Run validation testing with Vinayak's QA suite
4. **Production Deployment**: Merge to CreatorCore main branch

## Support

For issues or questions:
- Check `handover_creatorcore_ready.md` for detailed documentation
- Review test files in `tests/` directory
- Check server logs in `reports/` directory

---

**Last Updated**: December 2, 2025  
**Version**: 1.0  
**Status**: Ready for Demo
