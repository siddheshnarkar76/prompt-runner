#main.py
import json
import logging
import os
import time
import uuid

import pandas as pd
import requests
import streamlit as st

from components.ui import prompt_input, log_viewer, action_buttons
from components.glb_viewer import render_glb_viewer, show_geometry_gallery
from utils.io_helpers import save_prompt, save_spec, load_prompts, load_logs
from agents.design_agent import prompt_to_spec
from agents.compliance_pipeline import run_compliance_pipeline
from utils.rule_explanation import format_rule_outcome
from utils.geometry_converter import json_to_glb, create_building_geometry
from core_bridge import sync_run_log

logger = logging.getLogger("prompt_runner")
ORCH_ENDPOINT = os.environ.get("ORCHESTRATE_URL", "http://127.0.0.1:5001/orchestrate/run")

st.set_page_config(page_title="Prompt Runner", layout="wide")
st.title("📝 Streamlit Prompt Runner")

# --- Prompt Input ---
user_prompt = prompt_input()
json_spec = None
case_id = None

if st.button("Submit", key="submit_main"):
    if user_prompt:
        spec_data = prompt_to_spec(user_prompt)
        spec_filename = save_spec(spec_data)
        save_prompt(user_prompt, spec_filename)
        case_id = os.path.splitext(spec_filename)[0]
        
        # Log to Core
        sync_run_log({
            "case_id": case_id,
            "event": "prompt_submitted",
            "prompt": user_prompt,
            "output": spec_data,
            "spec_filename": spec_filename
        })
        
        st.success("Prompt processed successfully!")
    else:
        st.error("Please enter a prompt.")

# --- Load Latest JSON Spec ---
if os.path.exists("data/specs") and user_prompt:
    last_spec_files = sorted(os.listdir("data/specs"), reverse=True)
    if last_spec_files:
        spec_file = os.path.join("data/specs", last_spec_files[0])
        with open(spec_file) as f:
            json_spec = json.load(f)
        case_id = os.path.splitext(last_spec_files[0])[0]
        
        st.markdown("### Generated JSON Specification")
        st.json(json_spec)

# --- Feedback Section ---
if json_spec and case_id:
    st.markdown("### Feedback")
    col1, col2 = st.columns(2)
    feedback_api = "http://127.0.0.1:5001/api/mcp/feedback"
    
    if col1.button("👍 Good result"):
        feedback_input = {
            "case_id": case_id,
            "feedback": 1
        }
        try:
            r = requests.post(feedback_api, json=feedback_input, timeout=5)
            if r.status_code in [200, 201]:
                st.success(f"Feedback saved! Reward +2 | {r.json()}")
                
                # Log to Core
                sync_run_log({
                    "case_id": case_id,
                    "event": "feedback",
                    "feedback": "up",
                    "prompt": user_prompt if user_prompt else None,
                    "output": json_spec if json_spec else None
                })
            else:
                st.error(f"Failed to save feedback: {r.status_code}")
        except requests.exceptions.ConnectionError:
            st.warning("⚠️ MCP Server not running. Please start it with: `python mcp_server.py`")
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    if col2.button("👎 Needs improvement"):
        feedback_input = {
            "case_id": case_id,
            "feedback": -1
        }
        try:
            r = requests.post(feedback_api, json=feedback_input, timeout=5)
            if r.status_code in [200, 201]:
                st.error(f"Feedback saved! Reward -2 | {r.json()}")
                
                # Log to Core
                sync_run_log({
                    "case_id": case_id,
                    "event": "feedback",
                    "feedback": "down",
                    "prompt": user_prompt if user_prompt else None,
                    "output": json_spec if json_spec else None
                })
            else:
                st.error(f"Failed to save feedback: {r.status_code}")
        except requests.exceptions.ConnectionError:
            st.warning("⚠️ MCP Server not running. Please start it with: `python mcp_server.py`")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# --- Compliance Checker Agent ---
st.markdown("---")
st.markdown("### ✅ Compliance Checker")

comp_col1, comp_col2 = st.columns([1, 2])

with comp_col1:
    selected_city = st.selectbox("Select City", ["Mumbai", "Ahmedabad", "Pune", "Nashik"])
    
    st.markdown("**Planning Context (required):**")
    land_use_zone = st.selectbox("Land Use Zone", ["", "R1", "R2", "Commercial", "Industrial", "Mixed"], index=0)
    plot_area_sq_m = st.number_input("Plot Area (sq.m)", min_value=0.0, value=0.0, step=10.0)
    plot_width_m = st.number_input("Plot Width (m)", min_value=0.0, value=0.0, step=0.5)
    plot_frontage_m = st.number_input("Plot Frontage (m)", min_value=0.0, value=0.0, step=0.5)
    abutting_road_width_m = st.number_input("Abutting Road Width (m)", min_value=0.0, value=0.0, step=0.5)
    building_use = st.selectbox("Building Use", ["", "residential", "commercial", "mixed"], index=0)
    building_type = st.selectbox("Building Type", ["", "detached", "semi_detached", "apartment"], index=0)
    is_core_area = st.checkbox("Core Area", value=False)

    st.markdown("**Building Parameters:**")
    check_height = st.number_input("Height (m)", min_value=0.0, value=0.0, step=0.5)
    check_width = st.number_input("Width (m)", min_value=0.0, value=0.0, step=0.5)
    check_depth = st.number_input("Depth (m)", min_value=0.0, value=0.0, step=0.5)
    check_setback = st.number_input("Setback (m)", min_value=0.0, value=0.0, step=0.5)
    check_fsi = st.number_input("FSI", min_value=0.0, value=0.0, step=0.1)
    
    check_compliance = st.button("Check Compliance", type="primary")

with comp_col2:
    if check_compliance:
        with st.spinner("Checking compliance..."):
            try:
                # Mandatory planning validation (UI gate)
                mandatory_missing = []
                if not land_use_zone:
                    mandatory_missing.append("land_use_zone")
                if plot_area_sq_m <= 0:
                    mandatory_missing.append("plot_area_sq_m")
                if abutting_road_width_m <= 0:
                    mandatory_missing.append("abutting_road_width_m")
                if not building_use:
                    mandatory_missing.append("building_use")

                if mandatory_missing:
                    st.error("Missing mandatory planning parameters: " + ", ".join(mandatory_missing))
                else:
                    # Build spec overrides in canonical schema
                    subject = {
                        "case_id": str(uuid.uuid4())[:8],
                        "city": selected_city,
                        "land_use_zone": land_use_zone,
                        "plot_area_sq_m": plot_area_sq_m,
                        "plot_width_m": plot_width_m or None,
                        "plot_frontage_m": plot_frontage_m or None,
                        "abutting_road_width_m": abutting_road_width_m,
                        "building_use": building_use,
                        "building_type": building_type or None,
                        "is_core_area": bool(is_core_area),
                        "height_m": check_height or None,
                        "fsi": check_fsi or None,
                        "setback_m": check_setback or None,
                        # Geometry helpers
                        "width_m": check_width or None,
                        "depth_m": check_depth or None,
                    }
                
                    # Run compliance pipeline (MANDATORY FIXES version)
                    # Load rules from JSON file
                    rules_file = "data/mcp/rules/rules.json"
                    loaded_rules = []
                    if os.path.exists(rules_file):
                        try:
                            with open(rules_file, 'r') as f:
                                all_rules_by_city = json.load(f)
                            loaded_rules = all_rules_by_city.get(selected_city, [])
                            st.sidebar.info(f"Loaded {len(loaded_rules)} rules for {selected_city}")
                        except Exception as e:
                            st.sidebar.warning(f"Could not load rules: {e}")
                            loaded_rules = []

                    pipeline_output = run_compliance_pipeline(
                        prompt=f"{selected_city} building",
                        city=selected_city,
                        rules=loaded_rules,
                        spec_override=subject
                    )
                
                    # Extract results from pipeline output
                    case_id_comp = pipeline_output.get("case_id")
                    status = pipeline_output.get("status")
                    evaluations = pipeline_output.get("evaluations", [])
                    geometry_path = pipeline_output.get("geometry", {}).get("path")

                    # Log compliance check to Core
                    sync_run_log({
                        "case_id": case_id_comp,
                        "event": "compliance_check",
                        "city": selected_city,
                        "subject": subject,
                        "status": status,
                        "output": pipeline_output
                    })

                    # Display results
                    if status == "BLOCKED":
                        st.error(pipeline_output.get("reason"))
                        st.info(f"Missing: {pipeline_output.get('missing_fields', [])}")
                    elif status == "ERROR":
                        st.error(pipeline_output.get("reason"))
                    else:
                        st.success(f"✅ Compliance check status: {status} (case_id: {case_id_comp})")
                        st.info(f"Found {len(evaluations)} applicable rules")

                        # Display each evaluation
                        for idx, evaluation in enumerate(evaluations):
                            clause_no = evaluation.get("clause_no", f"Rule_{idx}")
                            checks = evaluation.get("checks", {})
                            ok = all(item.get("ok", True) for item in checks.values()) if checks else True

                            status_icon = "✅" if ok else "❌"
                            with st.expander(f"{status_icon} Clause {clause_no}"):
                                for check_name, check_result in checks.items():
                                    if isinstance(check_result, dict):
                                        st.write(f"- {check_name}: subject={check_result.get('subject')} rule_min={check_result.get('rule_min')} rule_max={check_result.get('rule_max')} ok={check_result.get('ok')}")
                                    else:
                                        st.write(f"- {check_name}: {check_result}")
                                with st.expander("Full Details"):
                                    st.json(evaluation)

                        # Display geometry if generated
                        if geometry_path and os.path.exists(geometry_path):
                            st.markdown("### Generated 3D Geometry")
                            render_glb_viewer(geometry_path, height=400)
                        
            except Exception as e:
                st.error(f"Error: {str(e)}")

# --- Orchestrator (API-run) ---
st.markdown("---")
st.markdown("### 🎯 Orchestrate (server run)")

orch_city = st.selectbox(
    "City for orchestrator run",
    ["Mumbai", "Ahmedabad", "Pune", "Nashik"],
    key="orch_city_select",
)

orch_prompt_default = user_prompt or "Design a mid-rise residential building"
orch_prompt = st.text_input(
    "Prompt to orchestrate",
    value=orch_prompt_default,
    key="orch_prompt_input",
)

if st.button("Run Orchestrator", key="orchestrate_run_btn"):
    if not orch_prompt.strip():
        st.warning("Enter a prompt before orchestrating.")
    else:
        subject_payload = {
            "height_m": check_height or None,
            "setback_m": check_setback or None,
            "width_m": check_width or None,
            "depth_m": check_depth or None,
            "fsi": check_fsi or None,
            "type": building_use or "residential",
        }
        subject_payload = {k: v for k, v in subject_payload.items() if v not in (None, 0, 0.0, "")}

        orch_body = {
            "session_id": f"orch_{uuid.uuid4().hex[:8]}",
            "city": orch_city,
            "prompt": orch_prompt.strip(),
            "subject": subject_payload,
            "metadata": {"source": "streamlit"},
        }

        try:
            resp = requests.post(ORCH_ENDPOINT, json=orch_body, timeout=15)
            if resp.status_code in (200, 201):
                data = resp.json()
                outcomes_count = len(data.get("outcomes", []))
                st.success(f"Orchestrator run saved (run_id={data.get('run_id')}, outcomes={outcomes_count}).")
                with st.expander("Response", expanded=False):
                    st.json(data)
            else:
                st.error(f"Orchestrator failed: status {resp.status_code}")
        except requests.exceptions.ConnectionError:
            st.warning("⚠️ Orchestrator API not reachable at 5001. Start FastAPI with `python api/main.py`.")
        except Exception as e:
            st.error(f"Error running orchestrator: {str(e)}")

# --- 3D Geometry Viewer Section ---
st.markdown("---")
st.markdown("### 🏗️ 3D Geometry Viewer")

tab1, tab2 = st.tabs(["📊 Current Model", "🗂️ Gallery View"])

with tab1:
    if case_id:
        geometry_path = os.path.join("outputs", "geometry", f"{case_id}.glb")
        if os.path.exists(geometry_path):
            st.markdown(f"**3D Model for Case:** `{case_id}`")
            render_glb_viewer(geometry_path, height=500)
        else:
            st.info("No 3D geometry generated yet for this case.")
    else:
        st.info("Submit a prompt to generate and view 3D geometry.")

with tab2:
    show_geometry_gallery()

# --- Divider ---
st.markdown("---")
st.markdown("### History")

logs = load_logs()
prompt_logs = logs.get("prompt_logs", [])
action_logs = logs.get("action_logs", [])

with st.container():
    col_left, col_right = st.columns([1, 1], gap="large")

    # Prompt Logs
    with col_left:
        st.markdown("**Prompt Logs**")
        if prompt_logs:
            df = pd.DataFrame(prompt_logs)
            df["prompt_preview"] = df["prompt"].apply(lambda s: s[:100]+"…" if len(s)>100 else s)
            display_df = df[["id","timestamp","prompt_preview","spec_filename"]].sort_values("timestamp", ascending=False)
            st.dataframe(display_df, height=260)
        else:
            st.info("No prompt logs available.")

    # Action Logs
    with col_right:
        st.markdown("**Action Logs**")
        if action_logs:
            adf = pd.DataFrame(action_logs)
            adf["details_summary"] = adf["details"].apply(lambda d: ", ".join(f"{k}:{v}" for k,v in d.items()) if d else "")
            display_adf = adf[["timestamp","action","spec_id","details_summary"]].sort_values("timestamp", ascending=False)
            st.dataframe(display_adf, height=260)
        else:
            st.info("No action logs available.")

# --- Sidebar Log Viewer ---
st.sidebar.header("Log Viewer")
past_prompts = load_prompts()
selected_prompt = log_viewer(past_prompts)

if selected_prompt:
    spec_file = os.path.join("data/specs", f"{selected_prompt}.json")
    if os.path.exists(spec_file):
        with open(spec_file) as f:
            spec_data = json.load(f)
        with st.sidebar.expander("📄 View JSON Spec"):
            st.json(spec_data)
    else:
        st.sidebar.warning("Spec file not found for this prompt.")

# --- Action Buttons in Sidebar ---
action_buttons(selected_prompt)
