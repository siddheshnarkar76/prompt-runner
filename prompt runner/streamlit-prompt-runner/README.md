# Prompt Runner - Building Compliance & Design Validation Platform

A production-ready platform for validating building designs against municipal compliance rules. Submit design prompts → receive compliance assessments and 3D geometry outputs.

**Tech Stack:** FastAPI + Streamlit + MongoDB Atlas + Python 3.11+

---

## **Quick Start (5 minutes)**

### **1. Clone & Setup**

```bash
cd path/to/project
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate   # macOS/Linux

pip install --upgrade pip
pip install -r requirements.txt
```

### **2. Configure MongoDB**

Create `.env` file in project root with your MongoDB Atlas credentials:

```
USE_MOCK_MONGO=0
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?appName=prompt-runner
MONGO_DB=prompt_runner
```

**Get MongoDB credentials:**
1. Go to [mongodb.com/cloud/atlas](https://mongodb.com/cloud/atlas)
2. Create cluster → Database User → Get connection string
3. **Important:** URL-encode special characters (e.g., `@` → `%40`)

### **3. Start Services (3 terminals)**

**Terminal 1 - API:**
```powershell
uvicorn api.main:app --reload --host 127.0.0.1 --port 5001
```

**Terminal 2 - Streamlit UI:**
```powershell
streamlit run main.py
```

**Terminal 3 - MCP Server (optional):**
```powershell
python mcp_server.py
```

Then open:
- **UI:** http://localhost:8501
- **API:** http://127.0.0.1:5001

---

## **Local Development (No MongoDB)**

For testing without MongoDB Atlas:

```powershell
$env:USE_MOCK_MONGO = "1"  # Uses in-memory mongomock
uvicorn api.main:app --reload --host 127.0.0.1 --port 5001
streamlit run main.py
```

---

## **Project Structure**

```
streamlit-prompt-runner/
├── main.py                    # Streamlit UI entry point
├── platform_adapter.py        # Production integration layer
├── mcp_server.py              # MCP server entry point
├── requirements.txt           # Dependencies (pinned versions)
├── .env                       # Environment config (not committed)
│
├── api/                       # FastAPI backend
│   ├── main.py               # API entry point
│   ├── orchestrator.py       # Compliance pipeline orchestration
│   ├── routes.py             # REST endpoints
│   └── health.py             # Health check endpoint
│
├── agents/                    # Core business logic
│   ├── compliance_pipeline.py # Main compliance checker
│   ├── design_agent.py        # Design spec generator
│   ├── rule_classification_agent.py # Rule classifier
│   ├── calculator_agent.py    # Calculation engine
│   └── ...
│
├── components/               # Streamlit UI components
│   ├── ui.py                # UI helpers (input, buttons, history)
│   └── glb_viewer.py        # 3D geometry viewer
│
├── mcp/                      # MongoDB & schemas
│   ├── db.py                # MongoDB connection (singleton)
│   ├── schemas.py           # Request/response validation
│   └── ...
│
├── schemas/                  # Contract definitions
│   ├── contract.json        # Input/output schema
│   └── demo_run.json        # Golden demo reference
│
├── tests/                    # Test suite
│   ├── test_integration.py
│   └── conftest.py
│
└── utils/                    # Utility functions
    ├── io_helpers.py        # File I/O & logging
    ├── geometry_converter.py # 3D model generation
    └── ...
```

---

## **Key Features**

### **1. Compliance Checking**
- Validates building designs against city-specific rules
- Supports: Mumbai, Pune, Ahmedabad, Nashik
- Returns: compliance status, rule evaluations, geometry

### **2. Design Input**
- Natural language prompt: `"Design a 5-story residential building"`
- Structured parameters: height, width, depth, setback, FSI
- Automatic defaults if parameters missing

### **3. 3D Visualization**
- Auto-generates 3D GLB models from specifications
- Interactive viewer in Streamlit UI

### **4. Feedback Loop**
- Users can rate compliance checks (👍 good / 👎 needs improvement)
- Feedback stored in MongoDB for learning/refinement

### **5. Production Integration**
- Stable API entrypoint: `platform_adapter.py::run_from_platform()`
- Schema-locked contracts: `schemas/contract.json`
- Trace ID support for distributed tracing

---

## **API Endpoints**

### **Compliance Check (Main)**
```
POST /orchestrate/run
Content-Type: application/json

{
  "prompt": "Design a mid-rise residential building",
  "city": "Mumbai",
  "subject": {
    "height_m": 25,
    "width_m": 50,
    "depth_m": 40
  }
}

Response:
{
  "success": true,
  "trace_id": "uuid",
  "case_id": "case_001",
  "compliance_status": {
    "status": "compliant",
    "rules_evaluated": 5,
    "rules_passed": 5,
    "rules_failed": 0
  }
}
```

### **Health Check**
```
GET /health
Response: { "status": "healthy", "mongodb": "connected" }
```

### **Feedback**
```
POST /api/mcp/feedback
{
  "case_id": "case_001",
  "feedback": 1  # +1 for good, -1 for bad
}
```

See [INTEGRATION_HANDOVER.md](INTEGRATION_HANDOVER.md) for full API documentation.

---

## **Testing**

### **Run All Tests**
```powershell
pytest -v
```

### **Validate Integration**
```powershell
python validate_integration.py
```

### **Test with Demo Mode (Deterministic)**
```powershell
$env:DEMO_MODE = "1"
$env:USE_MOCK_MONGO = "1"
python validate_integration.py
```

---

## **Environment Variables**

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_MOCK_MONGO` | `1` | Use in-memory mongomock (0 = real MongoDB) |
| `MONGO_URI` | N/A | MongoDB Atlas connection string |
| `MONGO_DB` | `prompt_runner` | Database name |
| `DEMO_MODE` | `0` | Enable deterministic demo mode |
| `ORCHESTRATE_URL` | `http://127.0.0.1:5001/orchestrate/run` | API endpoint |

---

## **Troubleshooting**

### **MongoDB Connection Failed**
```
Error: Username and password must be escaped according to RFC 3986
```
**Fix:** URL-encode special characters in password. Use `%40` for `@`, etc.

### **Port Already in Use**
```
Error: Address already in use
```
**Fix:** Change port: `uvicorn api.main:app --port 5002`

### **No Collections in MongoDB**
Collections are created automatically when data is inserted. Submit a prompt in Streamlit to create them.

---

## **Documentation**

- [PROJECT_GUIDE.md](PROJECT_GUIDE.md) — Detailed project overview
- [INTEGRATION_HANDOVER.md](INTEGRATION_HANDOVER.md) — Platform integration guide
- [INTEGRATION_READINESS.md](INTEGRATION_READINESS.md) — Readiness checklist
- [ACCEPTANCE_CHECKLIST.md](ACCEPTANCE_CHECKLIST.md) — Acceptance criteria

---

## **Contributing**

1. Create a feature branch: `git checkout -b feature/xyz`
2. Make changes and commit: `git commit -m "feat: description"`
3. Push and create PR: `git push origin feature/xyz`

---

## **License**

Proprietary - BHIV AI Platform Integration

---

## **Support**

For issues or questions:
1. Check [INTEGRATION_HANDOVER.md](INTEGRATION_HANDOVER.md)
2. Run `validate_integration.py` to diagnose issues
3. Check logs in `reports/core_sync.json` and `data/logs/`

---

**Version:** 2.0.0  
**Last Updated:** 2026-01-28
