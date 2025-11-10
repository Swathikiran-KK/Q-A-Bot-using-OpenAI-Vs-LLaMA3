import streamlit as st
import pandas as pd
from components.ui import page_header, section_divider, note
from utils.config import OPENROUTER_API_KEY, GROQ_API_KEY, JINA_API_KEY, QDRANT_URL, QDRANT_API_KEY
from analytics.tracker import MetricsTracker

st.set_page_config(page_title="LLM Comparison Workbench", page_icon="⚖️", layout="wide", initial_sidebar_state="expanded")

# Ensure tracker and load past CSV if any
if "tracker" not in st.session_state:
    st.session_state.tracker = MetricsTracker()
    st.session_state.tracker.load_csv()

with st.sidebar:
    st.markdown("### Navigate")
    st.page_link("pages/1_Text_Compare.py", label="📝 Text Compare")
    st.page_link("pages/2_Multimodal_Compare.py", label="🖼️ Images & Docs")
    st.page_link("pages/3_RAG_Compare.py", label="📚 RAG Compare")
    st.page_link("pages/4_Analytics.py", label="📊 Analytics")
    st.page_link("pages/5_Settings.py", label="⚙️ Settings")
    st.markdown("---")
    st.caption("Run comparisons, then open Analytics.")

page_header(
    "LLM Comparison Workbench",
    "Free-only: Images & Documents (PDF/DOCX/CSV/TXT), Text compare, and RAG.",
    kicker="Homepage"
)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.button("Start Text Compare →", type="primary", use_container_width=True, on_click=lambda: st.switch_page("pages/1_Text_Compare.py"))
with c2:
    st.button("Images & Docs →", type="primary", use_container_width=True, on_click=lambda: st.switch_page("pages/2_Multimodal_Compare.py"))
with c3:
    st.button("RAG with PDF →", type="primary", use_container_width=True, on_click=lambda: st.switch_page("pages/3_RAG_Compare.py"))
with c4:
    st.button("Open Analytics →", type="primary", use_container_width=True, on_click=lambda: st.switch_page("pages/4_Analytics.py"))

section_divider()
st.subheader("Status")
s1, s2, s3, s4 = st.columns(4)
with s1: st.write("**OpenAI via OpenRouter**"); st.write("Key:", "✅" if OPENROUTER_API_KEY else "❌")
with s2: st.write("**Groq (Llama-3.1)**"); st.write("Key:", "✅" if GROQ_API_KEY else "❌")
with s3: st.write("**Jina (optional)**"); st.write("Key:", "✅" if JINA_API_KEY else "—")
with s4: st.write("**Qdrant (optional)**"); st.write("URL:", "✅" if (QDRANT_URL and QDRANT_API_KEY) else "—")

section_divider()
st.subheader("Recent runs")
df = st.session_state.tracker.df()
if not df.empty:
    # Backward-compat: compute a small view regardless of column names
    cols = []
    for c in ["openai_latency","llama_latency","openrouter_latency","groq_latency"]:
        if c in df.columns: cols.append(c)
    view_cols = ["timestamp","mode","preference"] + cols
    show = [c for c in view_cols if c in df.columns]
    st.dataframe(df[show].tail(6).iloc[::-1], use_container_width=True)
    st.caption("Runs are saved automatically from the compare pages.")
else:
    note("No runs yet — jump into a page above to log your first comparison.")
