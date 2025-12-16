# How to Run Feedback Flow Test Successfully

## Issue

The `feedback_flow.json` shows all tests failing because the **MCP server is not running**.

## Solution

The feedback flow test requires the MCP server to be running. Follow these steps:

### Step 1: Start the MCP Server

Open a terminal and run:

```bash
cd streamlit-prompt-runner
python mcp_server.py
```

You should see output like:
```
 * Running on http://127.0.0.1:5001
```

**Keep this terminal open** - the server must stay running.

### Step 2: Verify Server is Running

In a new terminal, test the connection:

```bash
curl http://localhost:5001/
```

You should get a JSON response.

### Step 3: Run the Feedback Flow Test

In the new terminal:

```bash
cd streamlit-prompt-runner
python test_feedback_flow.py
```

### Expected Output

With the server running, you should see:

```
Testing CreatorCore Feedback Integration...
============================================================

Test Case 1: mumbai_test_001 - up (Mumbai)
  ✓ Success: reward=2, legacy=True, core=True

Test Case 2: pune_test_001 - down (Pune)
  ✓ Success: reward=-2, legacy=True, core=True

Test Case 3: mumbai_test_001 - up (Mumbai)
  ✓ Success: reward=2, legacy=True, core=True

Testing Cumulative Scoring...
  mumbai_test_001: confidence=1.0, count=2
  pune_test_001: confidence=-1.0, count=1

============================================================
Test Results:
  Server Running: Yes ✓
  Total Tests: 3
  Successful: 3
  Success Rate: 100.0%
  Status: PASS

Report saved to: reports/feedback_flow.json
============================================================
```

## Troubleshooting

### Issue: "Connection refused" or "Server not running"

**Solution**: Make sure the MCP server is running in another terminal.

### Issue: "MongoDB connection failed"

**Solution**: 
1. Make sure MongoDB is running
2. Check your `MONGO_URI` environment variable
3. Verify MongoDB connection in `db_connection.py`

### Issue: Tests still fail even with server running

**Solution**:
1. Check server logs for errors
2. Verify endpoints are accessible:
   ```bash
   curl http://localhost:5001/core/feedback -X POST -H "Content-Type: application/json" -d '{"case_id":"test","feedback":1}'
   ```
3. Check MongoDB collections exist

## Alternative: Test Without Server (Mock Mode)

If you can't run the server, you can still test the code structure, but feedback won't actually be saved. The test will show warnings but continue.

## Next Steps

Once the test passes:
1. Check `reports/feedback_flow.json` - should show `"integration_status": "PASS"`
2. Verify feedback was saved in MongoDB `creator_feedback` collection
3. Check cumulative scoring is working

---

**Note**: The improved test script now detects if the server is running and provides helpful error messages.


