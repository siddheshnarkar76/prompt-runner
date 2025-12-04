# Streamlit Prompt Runner

## Overview

The **Streamlit Prompt Runner** is a web application for urban planning compliance checking with 3D visualization. It allows users to input prompts, generate structured JSON specifications, check building compliance against DCR regulations, and visualize buildings in 3D.

The backend is now **integrated with CreatorCore** via a unified bridge, with:
- Standardized logging and feedback APIs
- Unified feedback memory (`creator_feedback` collection)
- Health and diagnostics endpoints for automated monitoring

---

## ✨ Features

- 🎨 **AI-Powered Design** - Natural language → JSON specifications
- ✅ **Compliance Checking** - Multi-city DCR regulation validation
- 🏗️ **3D Visualization** - Interactive GLB model viewer
- 👍👎 **RL Feedback System** - Reinforcement learning from user feedback
- 🌆 **Multi-City Support** - Mumbai, Ahmedabad, Pune, Nashik
- 📊 **Complete Logging** - Prompt and action tracking
- 🧪 **Tested** - 82 tests with 94% pass rate

---

## 🚀 Quick Start

### Installation

```bash
# 1. Clone repository
cd "C:\prompt runner\streamlit-prompt-runner"

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables (or use .env)
export MONGO_URI="mongodb://localhost:27017"
export MONGO_DB="mcp_database"
export CREATORCORE_BASE_URL="http://localhost:5001"

# 4. Start MongoDB (if not running)
mongod

# 5. Start MCP / CreatorCore bridge server (Terminal 1)
python mcp_server.py

# 6. Start Streamlit App (Terminal 2)
streamlit run main.py

# 7. Open browser
http://localhost:8501
```

---

## 🔌 CreatorCore Integration

### Bridge Client

The CreatorCore bridge client in `creatorcore_bridge/bridge_client.py` provides:
- `POST /core/log` – send prompt/output logs
- `POST /core/feedback` – send standardized feedback (1 / -1)
- `GET /core/context` – fetch recent interactions for prompt warming

Example:

```python
from creatorcore_bridge.bridge_client import get_bridge

bridge = get_bridge()
bridge.send_log(case_id="session_123", prompt="...", output={"city": "Mumbai"}, metadata={"city": "Mumbai"})
bridge.send_feedback(case_id="session_123", feedback=1, prompt="...", output={"result": "ok"})
context = bridge.get_context(user_id="user_123", limit=3)
```

### Health & Diagnostics

The MCP server (`mcp_server.py`) exposes CreatorCore-friendly health endpoints:

- `GET /system/health`
- `GET /creatorcore/health` (alias to match sprint spec)

Example response:

```json
{
  "status": "active",
  "core_bridge": true,
  "feedback_store": true,
  "last_run": "2025-12-02T08:25:32Z",
  "tests_passed": 85
}
```

Health checks and bridge syncs are logged under `reports/`:
- `reports/health_log.json`
- `reports/health_status.json`
- `reports/core_bridge_runs.json`

---

## 📋 Project Structure

```
streamlit-prompt-runner/
├── main.py                      # Main Streamlit application
├── mcp_server.py                # MCP + CreatorCore Flask API server
├── upload_rules.py              # Upload city rules to database
├── requirements.txt             # Python dependencies
│
├── creatorcore_bridge/          # CreatorCore bridge integration
│   ├── bridge_client.py         # Core bridge client (log/feedback/context)
│   └── log_converter.py         # Log format conversion utilities
│
├── agents/                      # AI Agents
│   ├── design_agent.py          # Prompt → JSON spec
│   ├── calculator_agent.py      # Compliance checking
│   ├── geometry_agent.py        # 3D generation
│   ├── evaluator_agent.py       # Rule-based evaluation agent (Mongo-backed)
│   └── rl_agent.py              # RL agent w/ CreatorCore feedback integration
│
├── components/                  # UI Components
│   ├── glb_viewer.py            # 3D GLB viewer
│   └── ui.py                    # UI helpers
│
├── utils/                       # Utilities
│   └── ...                      # Geometry, IO, helpers, etc.
│
├── tests/                       # Test Suite
│   ├── test_creatorcore_health.py   # Health & diagnostics tests
│   └── ...                          # Other tests
│
├── mcp_data/                    # Data Storage seeds
│   ├── rules.json
│   ├── geometry.json
│   └── feedback.json
│
└── outputs/                     # Generated outputs (JSON, geometry, etc.)
```

---

## 🎯 Usage

### **1. Design Studio**
Enter a prompt:
```
"Design a 7-story residential building in Mumbai with setback 3m"
```
Get structured JSON specification.

### **2. Compliance Checker**
- Select city (Mumbai/Ahmedabad/Pune/Nashik)
- Enter building parameters
- Check compliance against DCR regulations
- Get pass/fail results

### **3. 3D Viewer**
- View generated GLB models
- Interactive controls (rotate, zoom, pan)
- Download 3D files

### **4. Feedback System (CreatorCore + MCP)**
- 👍 Positive feedback (`"up"` → +2 reward, CreatorCore `feedback = 1`)
- 👎 Negative feedback (`"down"` → -2 reward, CreatorCore `feedback = -1`)
- Feedback is stored in:
  - Legacy MCP `feedback` collection
  - CreatorCore-style `creator_feedback` collection
- RL agent reads cumulative scoring before next run via `agents.rl_agent.get_feedback_before_next_run`

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run CreatorCore-related tests
pytest tests/test_creatorcore_* -v

# Run with coverage
pytest --cov=. --cov-report=html
```

Health and CreatorCore diagnostics are also summarized in:
- `reports/health_status.json`
- `reports/final_status.json`

---

## 🌆 Supported Cities

| City | Authority | Rules | Status |
|------|-----------|-------|--------|
| Mumbai | MCGM | 42 | ✅ |
| Ahmedabad | AMC | 3 | ✅ |
| Pune | PMC | 4 | ✅ |
| Nashik | NMC | 4 | ✅ |

**Total**: 53 rules

---

## 🔧 Configuration

### MCP Server
- **Port**: 5001
- **Database**: MongoDB
- **Endpoints**:
  - POST `/api/mcp/save_rule`
  - GET `/api/mcp/list_rules`
  - POST `/api/mcp/feedback`
  - POST `/api/mcp/geometry`

### Environment Variables
Create `.env` file:
```
MONGO_URI=mongodb://localhost:27017
MONGO_DB=mcp_database
```

---

## 📚 Documentation

- `QUICK_START.md` - Quick reference guide
- `FRONTEND_GUIDE.md` - Frontend user guide
- `handover_creatorcore_ready.md` - CreatorCore integration handover
- `TEST_RESULTS.md` - Testing documentation
- `tests/README.md` - Test suite guide

---

## 🤝 Contributing

Contributions welcome! Please:
1. Run tests before submitting
2. Follow existing code style
3. Update documentation
4. Add tests for new features

---

## 📄 License

MIT License

---

## 🎉 Acknowledgments

Built with:
- Streamlit
- Flask
- MongoDB
- Three.js
- Trimesh
- Pytest

---

**Status**: ✅ Production Ready, CreatorCore-integrated  
**Version**: 2.1  
**Last Updated**: December 4, 2025


