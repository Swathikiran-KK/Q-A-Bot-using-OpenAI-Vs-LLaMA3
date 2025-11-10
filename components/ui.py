# components/ui.py — minimal light UI helpers (no dark theme, no heavy CSS)
import streamlit as st
from typing import Dict, Optional

LIGHT_CSS = """
<style>
:root{
  --bg:#ffffff; --panel:#f7f8fb; --card:#ffffff; --border:#e6e8ef;
  --text:#0b1020; --sub:#4a5568; --accent:#2563eb;
}
html, body, [data-testid="stAppViewContainer"]{
  background: var(--bg);
  color: var(--text);
  font-feature-settings:"cv02","cv03","cv04","cv11";
}
[data-testid="stSidebar"]{
  background: var(--panel);
  border-right:1px solid var(--border);
}
.card{
  background: var(--card);
  border:1px solid var(--border);
  border-radius:14px;
  padding:16px;
}
.kicker{
  text-transform:uppercase; letter-spacing:.12em; color:var(--sub); font-size:.78rem;
}
.title{
  font-weight:800; letter-spacing:-.01em; margin:2px 0 2px 0;
}
.subtle{ color:var(--sub); }
.metric{
  display:flex; flex-direction:column; gap:2px; padding:10px 12px; border:1px solid var(--border); border-radius:12px; background:#fcfcff;
}
.metric .k{ font-size:12px; color:#6b7280;}
.metric .v{ font-size:18px; font-weight:700;}
hr.clean{ border:none; border-top:1px solid var(--border); margin:8px 0 16px 0;}
.badge{
  display:inline-block; padding:3px 8px; border-radius:999px; font-size:12px;
  border:1px solid var(--border); background:#f8fafc; color:#334155;
}
</style>
"""

def page_header(title: str, subtitle: Optional[str] = None, kicker: Optional[str] = None):
    """Top-of-page header, light and minimal."""
    st.markdown(LIGHT_CSS, unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        if kicker:
            st.markdown(f'<div class="kicker">{kicker}</div>', unsafe_allow_html=True)
        st.markdown(f'<h1 class="title">{title}</h1>', unsafe_allow_html=True)
        if subtitle:
            st.markdown(f'<div class="subtle">{subtitle}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

def metric_cards(metrics_left: Dict[str,str], metrics_right: Dict[str,str], left_title="Model A", right_title="Model B"):
    """Two-column metric stacks with simple cards."""
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**{left_title}**")
        _metric_stack(metrics_left)
    with c2:
        st.markdown(f"**{right_title}**")
        _metric_stack(metrics_right)

def _metric_stack(m: Dict[str,str]):
    cols = st.columns(3)
    items = list(m.items())
    for i in range(0, len(items), 3):
        row = items[i:i+3]
        cols = st.columns(len(row))
        for col, (k,v) in zip(cols, row):
            with col:
                st.markdown('<div class="metric">', unsafe_allow_html=True)
                st.markdown(f'<div class="k">{k}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="v">{v}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

def note(text: str):
    st.markdown(f'<div class="badge">{text}</div>', unsafe_allow_html=True)

def section_divider():
    st.markdown('<hr class="clean">', unsafe_allow_html=True)

def answer(title: str, body: str):
    """Simple answer card—kept generic to avoid name clashes."""
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f"**{title}**")
        st.write(body)
        st.markdown('</div>', unsafe_allow_html=True)
