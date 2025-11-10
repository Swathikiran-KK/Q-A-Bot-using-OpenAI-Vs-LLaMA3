import streamlit as st
from components.ui import page_header
from utils.config import (OPENROUTER_TEXT_MODEL, OPENROUTER_VISION_MODEL, GROQ_TEXT_MODEL)

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
page_header("Settings", "Models, costs & notes", "Config")

st.code(f"""
OpenAI via OpenRouter (text):   {OPENROUTER_TEXT_MODEL}
OpenAI via OpenRouter (vision): {OPENROUTER_VISION_MODEL}
Llama-3.1 via Groq (text):      {GROQ_TEXT_MODEL}
""", language="yaml")

st.markdown("""
- Light, minimal UI for readability.
- Multimodal: **Images** (OpenAI Vision) and **Documents** (PDF/DOCX/CSV/TXT) to both models.
- RAG: Hybrid BM25/TF-IDF + Vector (Qdrant+Jina when configured), blended retrieval.
- Add/adjust metrics in `evaluators/metrics.py`; render with `metric_cards`.
""")
