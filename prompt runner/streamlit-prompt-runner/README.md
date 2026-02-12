# Prompt Runner - Building Compliance & Design Validation Platform

A production-ready FastAPI platform for validating building designs against municipal compliance rules. Submit design prompts → receive compliance assessments and 3D geometry outputs.

**Tech Stack:** FastAPI + Python 3.11+ + JSON Storage

---

## **Quick Start (3 minutes)**

### **1. Clone & Setup**

```bash
cd "c:\Users\sid\Documents\prompt-main\prompt runner\streamlit-prompt-runner"
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate   # macOS/Linux

pip install --upgrade pip
pip install -r requirements.txt
```

### **2. Start FastAPI Server**

**Option 1 - Direct Start:**
```powershell
uvicorn api.main:app --reload --host 127.0.0.1 --port 5001
```

**Option 2 - Production Script:**
```powershell
python start_production.py
```

Then open:
- **API Docs:** http://localhost:5001/docs
- **Health Check:** http://localhost:5001/system/health

---

## **Project Structure**

```
streamlit-prompt-runner/
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
├── mcp/                      # Data storage (JSON files)
│   ├── db.py                 # JSON-based storage layer
│   └── schemas.py            # Data schemas
│
├── data/                     # Data files & storage
│   └── storage/              # JSON database files
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
