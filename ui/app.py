from __future__ import annotations

import os
import time

import httpx
import streamlit as st

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")

st.set_page_config(page_title="Debate Chamber", page_icon="⚖️", layout="wide")
st.title("Debate Chamber")
st.subheader("Multi-Agent LLM Deliberation System")

# --- Session state initialization ---
for key, default in [
    ("debate_id", None),
    ("topic", ""),
    ("phase_index", 0),
    ("rendered_phases", set()),
    ("rendered_verdict", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# --- Sidebar: new debate ---
with st.sidebar:
    st.header("New Debate")
    topic = st.text_input(
        "Topic or claim:",
        value="Did remote work reduce overall productivity?",
    )
    if st.button("Start Debate", type="primary"):
        try:
            resp = httpx.post(
                f"{ORCHESTRATOR_URL}/debate/start",
                json={"topic": topic},
                timeout=10.0,
            )
            data = resp.json()
            st.session_state.debate_id = data["debate_id"]
            st.session_state.topic = data["topic"]
            st.session_state.phase_index = 0
            st.session_state.rendered_phases = set()
            st.session_state.rendered_verdict = False
        except Exception as e:
            st.error(f"Failed to start debate: {e}")

# --- Active debate view ---
if not st.session_state.debate_id:
    st.info("Enter a topic and click **Start Debate** to begin.")
    st.stop()

debate_id = st.session_state.debate_id
st.header(f"Debate: {st.session_state.topic}")
st.caption(f"ID: `{debate_id}`")

# Fetch current state from the orchestrator
try:
    resp = httpx.get(
        f"{ORCHESTRATOR_URL}/debate/{debate_id}/responses",
        timeout=10.0,
    )
    data = resp.json()
except Exception as e:
    st.error(f"Failed to fetch debate state: {e}")
    st.stop()

if "error" in data:
    st.error(data["error"])
    st.stop()

state = data.get("state", "UNKNOWN")
current_phase = data.get("phase", "")
responses = data.get("responses", {})

# Status bar
status_colors = {
    "CREATED": "blue", "RUNNING": "orange", "COMPLETED": "green", "FAILED": "red",
}
color = status_colors.get(state, "gray")
st.markdown(f":{color}[**{state}**] — Phase: **{current_phase}**")

# Render phases in order
phase_order = ["OPENING", "REBUTTAL", "EVIDENCE", "SYNTHESIS", "VERDICT"]

for phase_name in phase_order:
    phase_data = responses.get(phase_name, [])
    if not phase_data:
        continue

    with st.expander(f"**{phase_name}** — {len(phase_data)} agent(s)", expanded=True):
        for resp_data in phase_data:
            agent_id = resp_data.get("agent_id", "unknown")
            stance = resp_data.get("stance", "")
            confidence = resp_data.get("confidence", 0)
            reasoning = resp_data.get("reasoning", "")

            agent_colors = {
                "skeptic": "#ff6b6b",
                "researcher": "#4ecdc4",
                "analyst": "#45b7d1",
            }
            agent_color = agent_colors.get(agent_id, "#888")

            st.markdown(
                f'<h3 style="color:{agent_color};margin:0;">'
                f'{agent_id.title()} Agent</h3>',
                unsafe_allow_html=True,
            )
            col1, col2, col3 = st.columns([1, 1, 4])
            col1.metric("Stance", stance)
            col2.metric("Confidence", f"{confidence:.0%}")
            col3.write(reasoning)

            # Extra fields
            extras = [
                ("evidence_refs", "Evidence"),
                ("challenges", "Challenges"),
                ("fallacies_detected", "Fallacies"),
                ("verified_claims", "Verified Claims"),
                ("disputed_claims", "Disputed Claims"),
                ("patterns_identified", "Patterns"),
                ("context_provided", "Context"),
            ]
            for field, label in extras:
                items = resp_data.get(field, [])
                if items:
                    with st.expander(f"{label} ({len(items)})"):
                        for item in items:
                            st.write(f"- {item}")

            if resp_data.get("synthesis"):
                st.markdown("**Synthesis:**")
                st.write(resp_data["synthesis"])

            st.divider()

# Verdict section
if state == "COMPLETED":
    st.success("Debate completed!")
    verdict_data = responses.get("VERDICT", [])
    for resp_data in verdict_data:
        if resp_data.get("agent_id") == "analyst":
            st.markdown("## Final Verdict")
            st.write(resp_data.get("reasoning", ""))
            if resp_data.get("synthesis"):
                st.markdown("**Synthesis:**")
                st.write(resp_data["synthesis"])

elif state == "FAILED":
    st.error("Debate failed. Check the server logs for details.")

# Auto-refresh while debate is running
if state in ("CREATED", "RUNNING"):
    time.sleep(3)
    st.rerun()
