# main.py
import json
import logging
import os
import uuid

import requests
import streamlit as st

from components.ui import prompt_input

logger = logging.getLogger("prompt_runner")

BASE_URL = os.environ.get("PROMPT_TO_JSON_URL", "http://127.0.0.1:8000")
DEFAULT_USERNAME = os.environ.get("PROMPT_TO_JSON_USERNAME", "admin")
DEFAULT_PASSWORD = os.environ.get("PROMPT_TO_JSON_PASSWORD", "bhiv2024")
# Control whether preview URLs are shown in the UI. Set SHOW_PREVIEW=1|true to enable.
SHOW_PREVIEW = os.environ.get("SHOW_PREVIEW", "false").lower() in ("1", "true", "yes")

st.set_page_config(page_title="Prompt Runner", layout="wide")
st.title("Prompt Runner")


def _auth_headers():
    token = st.session_state.get("auth_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def api_post(path: str, payload: dict | None = None, timeout: int = 30):
    url = f"{BASE_URL}{path}"
    return requests.post(url, json=payload, headers=_auth_headers(), timeout=timeout)


def api_get(path: str, params: dict | None = None, timeout: int = 30):
    url = f"{BASE_URL}{path}"
    return requests.get(url, params=params, headers=_auth_headers(), timeout=timeout)


def login(username: str, password: str):
    url = f"{BASE_URL}/api/v1/auth/login"
    resp = requests.post(url, data={"username": username, "password": password}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise ValueError("Auth token missing")
    st.session_state["auth_token"] = token
    st.session_state["auth_user"] = username
    return token


def show_response(resp: requests.Response):
    try:
        data = resp.json()
    except Exception:
        data = resp.text

    if resp.status_code >= 400:
        st.error(f"❌ {resp.status_code}")
        st.json(data)
    else:
        st.success(f"✅ {resp.status_code}")
        st.json(data)
    return data


with st.sidebar:
    st.header("🔐 Auth")
    username = st.text_input("Username", value=DEFAULT_USERNAME)
    password = st.text_input("Password", value=DEFAULT_PASSWORD, type="password")
    if st.button("Login"):
        try:
            login(username, password)
            st.success("Logged in")
        except Exception as e:
            st.error(f"Login failed: {str(e)}")

    if st.session_state.get("auth_token"):
        st.caption(f"Authenticated as: {st.session_state.get('auth_user')}")

if not st.session_state.get("auth_token"):
    st.warning("Login required for backend endpoints.")


tabs = st.tabs(
    [
        "Generate",
        "Switch",
        "Iterate",
        "Evaluate",
        "Compliance",
        "History",
        "Geometry",
        "Reports",
        "RL",
    ]
)

# --- Generate ---
with tabs[0]:
    st.subheader("Generate Design")
    prompt = prompt_input()
    city = st.selectbox("City", ["Mumbai", "Pune", "Ahmedabad", "Nashik", "Bangalore"], index=0)
    style = st.selectbox("Style", ["modern", "traditional", "contemporary", "rustic"], index=0)
    budget = st.number_input("Budget (INR)", min_value=0, value=0, step=100000)

    if st.button("Generate", key="generate_btn"):
        if not prompt or len(prompt) < 10:
            st.error("Prompt must be at least 10 characters")
        else:
            payload = {
                "user_id": st.session_state.get("auth_user", "user"),
                "prompt": prompt,
                "city": city,
                "style": style,
                "context": {"budget": budget} if budget > 0 else {},
            }
            try:
                resp = api_post("/api/v1/generate", payload, timeout=60)
                data = show_response(resp)
                if resp.status_code < 400:
                    st.session_state["last_spec_id"] = data.get("spec_id")
                    st.session_state["last_spec_json"] = data.get("spec_json")
                    st.session_state["last_preview_url"] = data.get("preview_url")
            except Exception as e:
                st.error(f"Generate failed: {str(e)}")

        if st.session_state.get("last_spec_json"):
            st.markdown("**Latest Spec**")
            st.json(st.session_state["last_spec_json"])
            # Preview URL is hidden by default. Enable by setting env SHOW_PREVIEW=1|true.
            if st.session_state.get("last_preview_url") and SHOW_PREVIEW:
                st.markdown(f"**Preview URL:** {st.session_state['last_preview_url']}")

# --- Switch ---
with tabs[1]:
    st.subheader("Switch Materials")
    spec_id = st.text_input("Spec ID", value=st.session_state.get("last_spec_id", ""))
    query = st.text_input("Change Request", placeholder="e.g., change wall to marble")
    if st.button("Apply Switch", key="switch_btn"):
        if not spec_id or not query:
            st.error("Spec ID and query are required")
        else:
            try:
                resp = api_post("/api/v1/switch", {"spec_id": spec_id, "query": query}, timeout=30)
                show_response(resp)
            except Exception as e:
                st.error(f"Switch failed: {str(e)}")

# --- Iterate ---
with tabs[2]:
    st.subheader("Iterate Design")
    spec_id = st.text_input("Spec ID", value=st.session_state.get("last_spec_id", ""), key="iter_spec_id")
    strategy = st.selectbox(
        "Strategy",
        ["auto_optimize", "improve_materials", "improve_layout", "improve_colors"],
        index=0,
    )
    if st.button("Iterate", key="iterate_btn"):
        if not spec_id:
            st.error("Spec ID is required")
        else:
            payload = {
                "user_id": st.session_state.get("auth_user", "user"),
                "spec_id": spec_id,
                "strategy": strategy,
            }
            try:
                resp = api_post("/api/v1/iterate", payload, timeout=60)
                show_response(resp)
            except Exception as e:
                st.error(f"Iterate failed: {str(e)}")

# --- Evaluate ---
with tabs[3]:
    st.subheader("Evaluate Design")
    spec_id = st.text_input("Spec ID", value=st.session_state.get("last_spec_id", ""), key="eval_spec_id")
    rating = st.slider("Rating", min_value=1, max_value=5, value=3)
    notes = st.text_area("Notes", height=80)
    feedback_text = st.text_area("Feedback", height=80)
    if st.button("Submit Evaluation", key="eval_btn"):
        if not spec_id:
            st.error("Spec ID is required")
        else:
            payload = {
                "user_id": st.session_state.get("auth_user", "user"),
                "spec_id": spec_id,
                "rating": rating,
                "notes": notes,
                "feedback_text": feedback_text,
            }
            try:
                resp = api_post("/api/v1/evaluate", payload, timeout=30)
                show_response(resp)
            except Exception as e:
                st.error(f"Evaluate failed: {str(e)}")

# --- Compliance ---
with tabs[4]:
    st.subheader("Compliance Check")
    city = st.selectbox("City", ["Mumbai", "Pune", "Ahmedabad", "Nashik"], key="comp_city")
    project_id = st.text_input("Project ID", value="project_001")
    land_use_zone = st.text_input("Land Use Zone", value="R1")
    plot_area_sq_m = st.number_input("Plot Area (sq.m)", min_value=0.0, value=100.0, step=10.0)
    abutting_road_width_m = st.number_input("Abutting Road Width (m)", min_value=0.0, value=12.0, step=0.5)
    height_m = st.number_input("Height (m)", min_value=0.0, value=10.0, step=0.5)
    setback_m = st.number_input("Setback (m)", min_value=0.0, value=3.0, step=0.5)
    fsi = st.number_input("FSI", min_value=0.0, value=1.8, step=0.1)

    if st.button("Run Compliance", key="compliance_btn"):
        case = {
            "case_id": f"case_{uuid.uuid4().hex[:8]}",
            "project_id": project_id,
            "city": city,
            "parameters": {
                "land_use_zone": land_use_zone,
                "plot_area_sq_m": plot_area_sq_m,
                "abutting_road_width_m": abutting_road_width_m,
                "height_m": height_m,
                "setback_m": setback_m,
                "fsi": fsi,
            },
        }
        try:
            resp = api_post("/api/v1/compliance/run_case", case, timeout=60)
            show_response(resp)
        except Exception as e:
            st.error(f"Compliance failed: {str(e)}")

# --- History ---
with tabs[5]:
    st.subheader("History")
    limit = st.number_input("Limit", min_value=1, value=20, step=1)
    project_id = st.text_input("Project ID (optional)", value="")
    if st.button("Load User History", key="history_btn"):
        try:
            params = {"limit": int(limit)}
            if project_id:
                params["project_id"] = project_id
            resp = api_get("/api/v1/history", params=params, timeout=30)
            show_response(resp)
        except Exception as e:
            st.error(f"History failed: {str(e)}")

    spec_id = st.text_input("Spec ID", value=st.session_state.get("last_spec_id", ""), key="hist_spec")
    spec_limit = st.number_input("Spec History Limit", min_value=1, value=50, step=1)
    if st.button("Load Spec History", key="spec_history_btn"):
        if not spec_id:
            st.error("Spec ID required")
        else:
            try:
                resp = api_get(f"/api/v1/history/{spec_id}", params={"limit": int(spec_limit)}, timeout=30)
                show_response(resp)
            except Exception as e:
                st.error(f"Spec history failed: {str(e)}")
# --- Geometry ---
with tabs[6]:
    st.subheader("Geometry")
    if st.button("List Geometry Files", key="geom_list"):
        try:
            resp = api_get("/api/v1/geometry/list", timeout=30)
            show_response(resp)
        except Exception as e:
            st.error(f"List failed: {str(e)}")

    request_id = st.text_input("Request ID", value=f"req_{uuid.uuid4().hex[:6]}")
    if st.button("Generate Geometry", key="geom_gen"):
        spec_json = st.session_state.get("last_spec_json")
        if not spec_json:
            st.error("Generate a spec first")
        else:
            payload = {"spec_json": spec_json, "request_id": request_id, "format": "glb"}
            try:
                resp = api_post("/api/v1/geometry/generate", payload, timeout=60)
                show_response(resp)
            except Exception as e:
                st.error(f"Geometry generation failed: {str(e)}")

# --- Reports ---
with tabs[7]:
    st.subheader("Reports")
    report_spec_id = st.text_input("Spec ID for Report", value=st.session_state.get("last_spec_id", ""), key="report_spec_id")
    if st.button("Get Report", key="report_btn"):
        if not report_spec_id:
            st.error("Spec ID required")
        else:
            try:
                resp = api_get(f"/api/v1/reports/{report_spec_id}", timeout=30)
                show_response(resp)
            except Exception as e:
                st.error(f"Report failed: {str(e)}")

# --- RL ---
with tabs[8]:
    st.subheader("RL Feedback & Training")
    spec_id = st.text_input("Spec ID", value=st.session_state.get("last_spec_id", ""), key="rl_spec_id")
    design_a_id = st.text_input("Design A ID", value=spec_id, key="rl_a")
    design_b_id = st.text_input("Design B ID", value="", key="rl_b")
    preference = st.selectbox("Preference", [1, -1, 0], index=0, format_func=lambda v: "A" if v == 1 else "B" if v == -1 else "Equal")
    if st.button("Submit RL Feedback", key="rl_feedback_btn"):
        payload = {"design_a_id": design_a_id, "design_b_id": design_b_id, "preference": preference}
        try:
            resp = api_post("/api/v1/rl/feedback", payload, timeout=30)
            show_response(resp)
        except Exception as e:
            st.error(f"RL feedback failed: {str(e)}")

    samples = st.number_input("RLHF Samples", min_value=10, value=100, step=10)
    if st.button("Train RLHF", key="rlhf_btn"):
        try:
            resp = api_post("/api/v1/rl/train/rlhf", {"num_samples": int(samples)}, timeout=60)
            show_response(resp)
        except Exception as e:
            st.error(f"RLHF failed: {str(e)}")

    iterations = st.number_input("PPO Iterations", min_value=10, value=50, step=10)
    if st.button("Train PPO", key="ppo_btn"):
        try:
            resp = api_post("/api/v1/rl/train/opt", {"num_iterations": int(iterations)}, timeout=120)
            show_response(resp)
        except Exception as e:
            st.error(f"PPO failed: {str(e)}")
