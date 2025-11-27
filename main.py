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
from agents.calculator_agent import calculator_agent
from utils.geometry_converter import json_to_glb, create_building_geometry
from utils import mcp_store
from core_bridge import sync_run_log
from agents.agent_clients import upload_parsed_pdf

logger = logging.getLogger("prompt_runner")

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

        try:
            upload_parsed_pdf(case_id, spec_data)
        except Exception as exc:
            logger.warning("Failed to upload spec %s to MCP: %s", case_id, exc)
        
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

# --- Display Latest JSON Spec ---
if os.path.exists("specs") and user_prompt:
    last_spec_files = sorted(os.listdir("specs"), reverse=True)
    if last_spec_files:
        spec_file = os.path.join("specs", last_spec_files[0])
        with open(spec_file) as f:
            json_spec = json.load(f)
        st.markdown("### Generated JSON Specification")
        st.json(json_spec)
        case_id = os.path.splitext(last_spec_files[0])[0]

# --- Feedback Section ---
if json_spec and case_id:
    st.markdown("### Feedback")
    col1, col2 = st.columns(2)
    feedback_api = "http://127.0.0.1:5001/api/mcp/feedback"
    
    if col1.button("👍 Good result"):
        feedback_input = {
            "case_id": case_id,
            "feedback": "up"
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
            "feedback": "down"
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
    
    st.markdown("**Building Parameters:**")
    check_height = st.number_input("Height (m)", min_value=1.0, value=21.0, step=1.0)
    check_width = st.number_input("Width (m)", min_value=5.0, value=30.0, step=1.0)
    check_depth = st.number_input("Depth (m)", min_value=5.0, value=20.0, step=1.0)
    check_setback = st.number_input("Setback (m)", min_value=0.0, value=3.0, step=0.5)
    check_fsi = st.number_input("FSI", min_value=0.1, value=2.0, step=0.1)
    
    check_compliance = st.button("Check Compliance", type="primary")

with comp_col2:
    if check_compliance:
        with st.spinner("Checking compliance..."):
            try:
                subject = {
                    "height_m": check_height,
                    "width_m": check_width,
                    "depth_m": check_depth,
                    "setback_m": check_setback,
                    "fsi": check_fsi,
                    "type": "residential"
                }
                
                results = calculator_agent(selected_city, subject)
                
                # Log compliance check to Core
                sync_run_log({
                    "case_id": f"compliance_{selected_city}_{int(time.time())}",
                    "event": "compliance_check",
                    "city": selected_city,
                    "subject": subject,
                    "output": {
                        "rule_count": len(results),
                        "results": results
                    }
                })
                
                st.success(f"✅ Found {len(results)} applicable rules")
                
                for idx, result in enumerate(results):
                    with st.expander(f"Rule: {result.get('clause_no', 'N/A')}"):
                        checks = result.get('checks', {})
                        
                        if 'height' in checks:
                            h = checks['height']
                            if h.get('ok') is True:
                                st.success(f"✅ Height: Compliant")
                            elif h.get('ok') is False:
                                st.error(f"❌ Height: Non-compliant")
                        
                        if 'fsi' in checks:
                            f = checks['fsi']
                            if f.get('ok') is True:
                                st.success(f"✅ FSI: Compliant")
                            elif f.get('ok') is False:
                                st.error(f"❌ FSI: Non-compliant")
                        
                        st.json(result)
                        
            except Exception as e:
                st.error(f"Error: {str(e)}")

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
    spec_file = os.path.join("specs", f"{selected_prompt}.json")
    if os.path.exists(spec_file):
        with open(spec_file) as f:
            spec_data = json.load(f)
        with st.sidebar.expander("📄 View JSON Spec"):
            st.json(spec_data)
    else:
        st.sidebar.warning("Spec file not found for this prompt.")

# --- Action Buttons in Sidebar ---
action_buttons(selected_prompt)
