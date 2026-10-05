import streamlit as st

from agent import run_agent

st.set_page_config(page_title="ResearchPilot", page_icon="🧭")
st.title("🧭 ResearchPilot")
st.caption("An AI agent that searches the web, reads pages, and writes a sourced report.")

MAX_QUESTIONS = 5  # per browser session, protects the shared free API limit

EXAMPLES = [
    "Compare the top 3 electric bike brands in Pakistan and give their price range.",
    "What is the latest stable version of Python and when was it released?",
    "If a laptop costs 85000 PKR and gets a 12% discount, what is the final price?",
]

if "count" not in st.session_state:
    st.session_state.count = 0
if "report" not in st.session_state:
    st.session_state.report = None


def set_question(q):
    st.session_state.question = q


st.write("Try an example:")
for ex in EXAMPLES:
    st.button(ex, on_click=set_question, args=(ex,))

question = st.text_area("Your research question", key="question", height=80)
go = st.button("🔍 Research", type="primary")

if go and question.strip():
    if st.session_state.count >= MAX_QUESTIONS:
        st.warning("Demo limit reached for this session. Please refresh the page.")
    else:
        st.session_state.count += 1
        st.session_state.report = None

        with st.status("Agent is working...", expanded=True) as status:
            for event in run_agent(question.strip()):
                if event["type"] == "tool_call":
                    name, args = event["name"], event["args"]
                    if name == "web_search":
                        st.write(f"🔍 Searching: **{args.get('query', '')}**")
                    elif name == "read_page":
                        st.write(f"📖 Reading: {args.get('url', '')}")
                    elif name == "calculator":
                        st.write(f"🧮 Calculating: `{args.get('expression', '')}`")
                elif event["type"] == "final":
                    st.session_state.report = event["content"]
                elif event["type"] == "error":
                    st.error(event["content"])
            status.update(label="Research complete", state="complete", expanded=False)

if st.session_state.report:
    st.markdown("---")
    st.markdown(st.session_state.report)
    st.download_button(
        "⬇️ Download report (.md)",
        st.session_state.report,
        file_name="research_report.md",
    )