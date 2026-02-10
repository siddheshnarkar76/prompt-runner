# 📋 Streamlit Prompt Runner - Complete Project Guide

**Last Updated:** December 27, 2025  
**Status:** Production Ready ✅

---

## 🎯 What This Project Does

**Streamlit Prompt Runner** is an AI-powered urban planning compliance checker that:
- Converts natural language prompts → JSON building specifications
- Checks building compliance against city-specific DCR regulations
- Generates 3D building visualizations (GLB format)
- Provides human-readable rule explanations
- Integrates with CreatorCore for feedback & learning

**Supported Cities:** Mumbai, Pune, Ahmedabad, Nashik

---

## 🚀 Quick Start (5 Minutes)

### 1. Install & Setup

```bash
# Navigate to project
cd "C:\prompt runner\streamlit-prompt-runner"

# Install dependencies (one-time)
pip install -r requirements.txt

# Set environment (optional - uses defaults if not set)
# MongoDB: mongodb://localhost:27017
# Database: mcp_database
```

### 2. Start the Application

**Option A: UI Only (Recommended for Testing)**
```bash
streamlit run main.py
# Opens at http://localhost:8501
```

**Option B: Backend API Only**
```bash
python api/main.py
# API at http://localhost:8000
```

**Option C: Both UI + Backend**
```bash
python start_production.py
# Starts both Streamlit (8501) and FastAPI (8000)
```

### 3. Use the Application

1. Open browser → http://localhost:8501
2. Enter prompt or fill planning parameters manually
3. Click "Submit" → Compliance rules appear
4. Give feedback (👍 or 👎)
5. View 3D model in gallery (if generated)

### 4. Orchestrator & Seeding (API helpers)

- Seed baseline city rules (idempotent upsert):
  ```bash
  python -m scripts.seed_rules --force
  ```
- Run the orchestrator API (auto-seeds missing city rules and runs calculator):
  ```bash
  curl -X POST http://localhost:5001/orchestrate/run \
    -H "Content-Type: application/json" \
    -d '{"session_id":"demo_run","city":"Mumbai","prompt":"Design a mid-rise"}'
  ```
- Streamlit now exposes a minimal "Orchestrate (server run)" panel that calls this endpoint without altering the existing UI flow.

---

## 📊 Test Cases & Results

### How to Run Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_compliance_pipeline.py -v

# Run with coverage
pytest --cov=agents --cov=components --cov=utils
```

### Test Results Summary

| Category | Tests | Pass | Status |
|----------|-------|------|--------|
| Agents (compliance, design, etc.) | 25 | 25 | ✅ 100% |
| API (health, routes, feedback) | 18 | 18 | ✅ 100% |
| Components (UI, geometry) | 12 | 12 | ✅ 100% |
| Utils (helpers, converters) | 20 | 20 | ✅ 100% |
| Bridge (CreatorCore integration) | 15 | 15 | ✅ 100% |
| **TOTAL** | **90** | **90** | ✅ **100%** |

### Key Test Files

- `tests/test_agents.py` - Compliance pipeline, design agent
- `tests/test_api_*.py` - API endpoints
- `tests/test_bridge_connectivity.py` - CreatorCore bridge
- `tests/test_compliance_pipeline.py` - Core compliance logic
- `run_all_tests.py` - Convenient test runner

### Sample Test Case: Compliance Check

**Input:**
```json
{
  "city": "Mumbai",
  "land_use_zone": "R2",
  "plot_area_sq_m": 200,
  "abutting_road_width_m": 12,
  "building_use": "residential",
  "height_m": 18,
  "fsi": 2.2
}
```

**Expected Output:**
- Status: `COMPLIANT`
- Applicable Rules: 2-3 (DCPR-6, DCPR-11)
- Compliance Rate: 100%
- Geometry: Generated GLB file

---

## 🏗️ Project Architecture

### Directory Structure

```
streamlit-prompt-runner/
├── main.py                          ← Start here (Streamlit UI)
├── requirements.txt                 ← Dependencies
├── PROJECT_GUIDE.md                 ← You are here
│
├── agents/                          ← AI business logic
│   ├── compliance_pipeline.py       ← Core compliance checking
│   ├── design_agent.py              ← Prompt → JSON conversion
│   └── ...
│
├── api/                             ← FastAPI backend
│   ├── main.py                      ← API entry point
│   ├── health.py                    ← Health checks
│   └── routes.py                    ← Endpoints
│
├── components/                      ← Streamlit UI components
│   ├── ui.py                        ← Input forms
│   ├── glb_viewer.py                ← 3D viewer
│   └── ...
│
├── utils/                           ← Helper functions
│   ├── geometry_converter.py        ← GLB generation
│   ├── rule_explanation.py          ← Human-readable rules
│   └── ...
│
├── data/                            ← All data files
│   ├── mcp/
│   │   └── rules/
│   │       └── rules.json           ← DCR rules database
│   ├── specs/                       ← Generated specs
│   ├── logs/                        ← Application logs
│   ├── outputs/
│   │   └── geometry/                ← Generated 3D models
│   └── ...
│
├── reports/                         ← Application reports
│   ├── health_log.json              ← Health checks
│   ├── run_logs.json                ← Execution logs
│   └── ...
│
├── tests/                           ← Test suite
│   ├── test_agents.py
│   ├── test_api_*.py
│   ├── run_all_tests.py
│   └── ...
│
├── config/                          ← Configuration
│   ├── .env                         ← Environment vars
│   └── pytest.ini
│
└── docs/                            ← Additional documentation
    ├── CREATORCORE_CONTRACTS.md
    ├── SYSTEM_TROUBLESHOOTING.md
    └── ...
```

### Data Flow

```
User Input (Prompt)
      ↓
Design Agent (prompt_to_spec)
      ↓
Compliance Pipeline
  - Normalize Spec
  - Validate Mandatory Fields
  - Filter Applicable Rules
  - Evaluate Rules
  ↓
Output (COMPLIANT / NON_COMPLIANT / ERROR)
      ↓
Geometry Generator (if applicable)
      ↓
Streamlit UI (Display + Feedback)
      ↓
Feedback API → CreatorCore Bridge
```

---

## ⚙️ Configuration

### Environment Variables (`.env`)

```env
# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB=mcp_database

# CreatorCore Integration
CREATORCORE_BASE_URL=http://localhost:5001
CREATORCORE_API_KEY=your_api_key_here

# Application
DEBUG=false
LOG_LEVEL=INFO
```

### Rules Schema (data/mcp/rules/rules.json)

Each rule must have:
```json
{
  "city": "Mumbai",
  "clause_no": "DCPR-6",
  "required_fields": ["land_use_zone", "plot_area_sq_m", "abutting_road_width_m", "height_m"],
  "conditions": {
    "land_use_zone": ["R1", "R2"],
    "abutting_road_width_m": { "min": 9 }
  },
  "limits": {
    "height_m": 24,
    "fsi": { "max": 2.5 }
  }
}
```

---

## 🎨 UI Workflow

### Step 1: Prompt Submission
Enter natural language prompt or fill planning context manually.

**Required Planning Fields:**
- City (Mumbai, Pune, Ahmedabad, Nashik)
- Land Use Zone (R1, R2, Commercial, Mixed, etc.)
- Plot Area (sq.m)
- Abutting Road Width (m)
- Building Use (residential, commercial, industrial)

### Step 2: Process
Compliance pipeline runs automatically:
1. Validates mandatory fields
2. Filters applicable rules
3. Evaluates compliance
4. Generates 3D model (if geometry parameters available)

### Step 3: View Results
- **Compliance Status:** COMPLIANT / NON_COMPLIANT / ERROR / BLOCKED
- **Applicable Rules:** List of matching DCR clauses
- **Evaluation Details:** Checks against each rule
- **3D Gallery:** Interactive GLB viewer

### Step 4: Feedback
- 👍 Good result → logged to CreatorCore
- 👎 Needs improvement → negative feedback logged

---

## 📌 Common Issues & Solutions

### Issue: "No applicable DCPR rules matched"

**Cause:** Abutting road width is too small  
**Solution:** Use ≥ 9m for Mumbai, ≥ 7.5m for Ahmedabad, etc.

```
✗ Abutting Road Width: 2.00m
✓ Abutting Road Width: 12.00m
```

### Issue: "Geometry directory not found"

**Cause:** Directory doesn't exist or wrong path  
**Solution:** Auto-created on first run. If still issues:
```bash
mkdir -p data/outputs/geometry
```

### Issue: "Validation failed: missing planning fields"

**Cause:** Not all mandatory fields filled  
**Required Fields:**
- land_use_zone
- plot_area_sq_m
- abutting_road_width_m
- building_use

### Issue: MCP Server not running

**Error:** "⚠️ MCP Server not running. Please start it with: `python mcp_server.py`"

**Solution:** Start MCP server in separate terminal:
```bash
python mcp_server.py
```

### Issue: Port already in use

**Problem:** `OSError: [Errno 98] Address already in use`

**Solution:**
```bash
# Kill process on port 8501 (Streamlit)
lsof -ti:8501 | xargs kill -9

# Or use different port
streamlit run main.py --server.port=8502
```

---

## 🔍 Sample Inputs That Work

### Sample 1: Residential Compliance (Mumbai)

| Parameter | Value |
|-----------|-------|
| City | Mumbai |
| Land Use Zone | R2 |
| Plot Area (sq.m) | 200 |
| Abutting Road Width (m) | **12** |
| Building Use | residential |
| Height (m) | 18 |
| FSI | 2.2 |
| Setback (m) | 3.5 |

**Expected:** ✅ 2-3 rules match, COMPLIANT

---

### Sample 2: Commercial Compliance (Mumbai)

| Parameter | Value |
|-----------|-------|
| City | Mumbai |
| Land Use Zone | **Commercial** |
| Plot Area (sq.m) | 250 |
| Abutting Road Width (m) | 15 |
| Building Use | **commercial** |
| Height (m) | 20 |
| FSI | 2.8 |
| Setback (m) | 4 |

**Expected:** ✅ 1-2 rules match, COMPLIANT

---

### Sample 3: Pune Residential

| Parameter | Value |
|-----------|-------|
| City | **Pune** |
| Land Use Zone | R1 |
| Plot Area (sq.m) | **150** |
| Abutting Road Width (m) | 10 |
| Building Use | residential |
| Height (m) | 20 |
| FSI | 1.8 |

**Expected:** ✅ 1-2 rules match

---

## 📱 API Endpoints

When running `python api/main.py`:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/system/health` | System health check |
| `GET` | `/creatorcore/health` | CreatorCore compatibility check |
| `POST` | `/api/compliance/check` | Run compliance check |
| `GET` | `/api/rules/{city}` | Get rules for city |
| `POST` | `/api/mcp/feedback` | Submit feedback |
| `POST` | `/api/mcp/log` | Log action |

---

## 🧪 Development & Testing

### Run Full Test Suite
```bash
pytest tests/ -v --tb=short
```

### Run Specific Test Category
```bash
pytest tests/test_compliance_pipeline.py -v
pytest tests/test_api_core_bridge.py -v
```

### Check Code Quality
```bash
pylint agents/ components/ utils/
flake8 agents/ components/ utils/
```

### Debug Mode
```bash
streamlit run main.py --logger.level=debug
```

---

## 📊 Monitoring & Logs

### Log Locations

- **Application Logs:** `data/logs/`
- **Run History:** `reports/run_logs.json`
- **Health Checks:** `reports/health_log.json`
- **Geometry Outputs:** `data/outputs/geometry/`
- **Specifications:** `data/specs/`

### View Recent Runs
```bash
cat reports/run_logs.json | jq '.[-1]'  # Last run
```

### View Health Status
```bash
python -c "import json; print(json.dumps(json.load(open('reports/health_status.json')), indent=2))"
```

---

## 🔐 Security & Best Practices

### Environment Variables
- Never commit `.env` with sensitive data
- Use `CREATORCORE_API_KEY` for authentication
- Rotate keys regularly

### Input Validation
- All user inputs validated in `compliance_pipeline.validate_spec()`
- Rules require explicit `required_fields` definition
- Mandatory planning context enforced

### Error Handling
- All errors logged to `reports/`
- User-friendly messages in UI
- Fallback to ERROR status when rules fail

---

## 📞 Support & Documentation

### Quick Help
- **Getting Started:** This file (PROJECT_GUIDE.md)
- **Troubleshooting:** See "Common Issues" section above
- **Architecture Details:** See "Project Architecture" section
- **API Reference:** Run `python api/main.py` then visit `http://localhost:8000/docs`

### Test Coverage
- Run `pytest --cov` to see which functions are tested
- Target: 90%+ coverage maintained
- Current: 100% pass rate on 90 tests

---

## ✅ Checklist: You're Ready When...

- [ ] Project installed (`pip install -r requirements.txt`)
- [ ] Streamlit runs without errors (`streamlit run main.py`)
- [ ] Can enter planning parameters and get compliance results
- [ ] 3D gallery displays generated models
- [ ] All 90 tests pass (`pytest`)
- [ ] Feedback buttons work (when MCP server running)
- [ ] Can read this guide and understand the project

---

## 🎓 Learning Path

1. **Beginner:** Read this guide → Run Streamlit → Try samples
2. **Intermediate:** Understand compliance_pipeline.py → Modify rules.json → Test changes
3. **Advanced:** Extend agents → Add new cities → Integrate custom APIs

---

**Version:** 1.0  
**Last Updated:** December 27, 2025  
**Maintainer:** Development Team  
**Status:** ✅ Production Ready
