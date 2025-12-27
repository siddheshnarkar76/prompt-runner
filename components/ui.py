import streamlit as st
import os
import shutil
from utils.io_helpers import load_logs, log_action

def prompt_input():
    return st.text_input("Enter your prompt:", key="prompt_input")

def log_viewer(logs):
    if not logs:
        st.sidebar.write("No prompts found.")
        return None

    selected = st.sidebar.selectbox("Select a past prompt", options=[l["id"] for l in logs], key="log_selectbox")
    if not selected:
        return None

    st.sidebar.write("Selected Prompt ID:", selected)

    # Show recent activity
    all_logs = load_logs()
    actions = all_logs.get("action_logs", [])
    related = [a for a in reversed(actions) if a.get("spec_id") == selected]

    card_html = "<div style='background:#f3f4f6;padding:10px;border-radius:8px;margin-top:8px;'>"
    card_html += "<strong>Recent Activities</strong>"
    if not related:
        card_html += "<div style='color:#6b7280;margin-top:6px;font-size:13px'>No actions recorded for this prompt.</div>"
    else:
        card_html += "<ul style='padding-left:18px;margin-top:6px;color:#111827'>"
        for act in related[:6]:
            ts = act.get("timestamp","")[:19].replace("T"," ")
            action = act.get("action")
            details = act.get("details") or {}
            detail_text = ""
            if details:
                detail_text = " — " + ", ".join(f"{k}:{v}" for k,v in details.items())
            card_html += f"<li style='margin-bottom:6px;font-size:13px'>{ts} — <b>{action}</b>{detail_text}</li>"
        card_html += "</ul>"
    card_html += "</div>"
    st.sidebar.markdown(card_html, unsafe_allow_html=True)

    return selected

def action_buttons(selected_prompt):
    if not selected_prompt:
        st.sidebar.info("Select a prompt to enable routing actions.")
        return

    spec_path = os.path.join("data/specs", f"{selected_prompt}.json")
    if not os.path.exists(spec_path):
        st.sidebar.error("Spec file not found for this prompt.")
        return

    st.sidebar.markdown("### 🚀 Actions")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("📤 Evaluator", key="send_evaluator"):
            target_dir = "data/send_to_evaluator"
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, f"{selected_prompt}.json")
            shutil.copy(spec_path, target_path)
            log_action("send_to_evaluator", selected_prompt, {"destination": target_path})
            st.sidebar.success(f"✅ Sent to Evaluator")
    
    with col2:
        if st.button("🎮 Unreal", key="send_unreal"):
            target_dir = "data/send_to_unreal"
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, f"{selected_prompt}.json")
            shutil.copy(spec_path, target_path)
            log_action("send_to_unreal", selected_prompt, {"destination": target_path})
            st.sidebar.success(f"✅ Sent to Unreal Engine")

