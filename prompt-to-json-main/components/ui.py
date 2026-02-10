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

    # format function to show prompt preview + timestamp while keeping full entry as value
    def fmt(entry):
        p = entry.get("prompt", "") or "(empty)"
        ts = entry.get("timestamp", "")[:19].replace("T", " ") if entry.get("timestamp") else ""
        preview = p[:100] + ("…" if len(p) > 100 else "")
        return f"{preview}  —  {ts}"

    selected_entry = st.sidebar.selectbox("Select a past prompt", options=logs, format_func=fmt, key="log_selectbox")
    if not selected_entry:
        return None

    st.sidebar.write("Selected Prompt:")
    st.sidebar.write(selected_entry.get("prompt", ""))

    # Show recent activity for this spec
    spec_id = selected_entry.get("spec_filename", "").replace(".json", "")
    all_logs = load_logs()
    actions = all_logs.get("action_logs", [])
    related = [a for a in reversed(actions) if a.get("spec_id") == spec_id]

    card_html = "<div style='background:#f3f4f6;padding:10px;border-radius:8px;margin-top:8px;'>"
    card_html += "<strong>Recent Activities</strong>"
    if not related:
        card_html += "<div style='color:#6b7280;margin-top:6px;font-size:13px'>No actions recorded for this prompt.</div>"
    else:
        card_html += "<ul style='padding-left:18px;margin-top:6px;color:#111827'>"
        for act in related[:6]:
            ts = act.get("timestamp", "")[:19].replace("T", " ")
            action = act.get("action")
            details = act.get("details") or {}
            detail_text = ""
            if details:
                detail_text = " — " + ", ".join(f"{k}:{v}" for k, v in details.items())
            card_html += f"<li style='margin-bottom:6px;font-size:13px'>{ts} — <b>{action}</b>{detail_text}</li>"
        card_html += "</ul>"
    card_html += "</div>"
    st.sidebar.markdown(card_html, unsafe_allow_html=True)

    return spec_id

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


def history_panel():
    """Polished searchable history timeline + gallery.

    - Search across prompts and spec ids
    - Filter by Prompts / Actions
    - Paginated timeline cards with spec preview and related actions
    """
    st.markdown("**History & Timeline**")
    logs = load_logs()
    prompt_logs = logs.get("prompt_logs", [])
    action_logs = logs.get("action_logs", [])

    # Controls
    cols = st.columns([3, 1, 1])
    search_q = cols[0].text_input("Search prompts / ids", key="history_search")
    filter_sel = cols[1].selectbox("Type", ["All", "Prompts", "Actions"], key="history_type")
    per_page = cols[2].selectbox("Per page", [5, 10, 20], index=1, key="history_per_page")

    # Build prompt-focused timeline entries
    def matches(q, text):
        if not q:
            return True
        return q.lower() in (text or "").lower()

    matched_prompts = [p for p in sorted(prompt_logs, key=lambda x: x.get("timestamp", ""), reverse=True)
                       if matches(search_q, (p.get("prompt", "") or "") + (p.get("spec_filename", "") or ""))]

    # Pagination
    page = st.session_state.get("history_page", 1)
    total = len(matched_prompts)
    pages = max(1, (total + per_page - 1) // per_page)
    page = st.number_input("Page", min_value=1, max_value=pages, value=page, key="history_page")
    start = (page - 1) * per_page
    end = start + per_page

    if filter_sel in ("All", "Prompts"):
        for p in matched_prompts[start:end]:
            pid = p.get("spec_filename", "").replace(".json", "")
            ts = p.get("timestamp", "")[:19].replace("T", " ")
            prompt_text = p.get("prompt", "")
            spec_fn = p.get("spec_filename")

            with st.container():
                cols = st.columns([8, 2])
                with cols[0]:
                    st.markdown(f"**{ts} — {pid}**")
                    st.write(prompt_text)
                    with st.expander("View JSON spec", expanded=False):
                        spec_path = os.path.join("data/specs", f"{pid}.json")
                        if os.path.exists(spec_path):
                            try:
                                with open(spec_path) as sf:
                                    spec = sf.read()
                                st.code(spec, language="json")
                            except Exception as e:
                                st.write("Could not load spec:", e)
                        else:
                            st.write("Spec file not found.")

                with cols[1]:
                    # related actions count
                    related = [a for a in action_logs if a.get("spec_id") == pid]
                    st.markdown(f"**Actions: {len(related)}**")
                    if related:
                        if st.button(f"Show actions {pid}", key=f"actions_{pid}"):
                            with st.expander("Related Actions", expanded=True):
                                for a in sorted(related, key=lambda x: x.get("timestamp"), reverse=True):
                                    ats = a.get("timestamp", "")[:19].replace("T", " ")
                                    st.write(f"- {ats} | {a.get('action')} — {a.get('details')}")

    if filter_sel in ("All", "Actions"):
        # Simple actions list (searchable)
        matched_actions = [a for a in sorted(action_logs, key=lambda x: x.get("timestamp", ""), reverse=True)
                           if matches(search_q, a.get("action", "") + str(a.get("spec_id", "")))]
        st.markdown("---")
        st.markdown("**Action Logs**")
        for a in matched_actions[:per_page]:
            ats = a.get("timestamp", "")[:19].replace("T", " ")
            st.write(f"{ats} — {a.get('action')} (spec: {a.get('spec_id')})")
            with st.expander("Details", expanded=False):
                st.json(a.get("details", {}))

    # Footer with counts
    st.markdown("---")
    st.caption(f"Showing {min(total, per_page)} of {total} prompts — page {page}/{pages}")

