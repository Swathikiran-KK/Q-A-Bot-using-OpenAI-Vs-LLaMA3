import streamlit as st, plotly.express as px, numpy as np, pandas as pd
from components.ui import page_header, section_divider

st.set_page_config(page_title="Analytics", page_icon="📊", layout="wide")
page_header("Analytics", "Explore saved comparisons and overall winner", "Reports")

# Ensure tracker
if "tracker" not in st.session_state:
    from analytics.tracker import MetricsTracker
    st.session_state.tracker = MetricsTracker()

df = st.session_state.tracker.df().copy()
if df.empty:
    st.info("No saved runs yet. Save from the compare pages.")
    st.stop()

# Normalize old column names (OpenRouter/Groq -> OpenAI/Llama)
col_map = {
    "openrouter_latency": "openai_latency",
    "groq_latency": "llama_latency",
    "openrouter_tokens_in": "openai_tokens_in",
    "openrouter_tokens_out": "openai_tokens_out",
    "groq_tokens_in": "llama_tokens_in",
    "groq_tokens_out": "llama_tokens_out",
    "openrouter_cost": "openai_cost",
    "groq_cost": "llama_cost",
    "coverage_openrouter": "coverage_openai",
    "coverage_groq": "coverage_llama",
    "readability_openrouter": "readability_openai",
    "readability_groq": "readability_llama",
    "citations_openrouter": "citations_openai",
    "citations_groq": "citations_llama",
    "openrouter_answer": "openai_answer",
    "groq_answer": "llama_answer",
}
for old, new in col_map.items():
    if old in df.columns and new not in df.columns:
        df[new] = df[old]

# Normalize vote strings
if "preference" in df.columns:
    df["preference"] = (
        df["preference"]
        .replace({
            "OpenRouter": "OpenAI (GPT-4o-mini)",
            "Groq": "Llama-3.1 (Groq)",
            "openrouter": "OpenAI (GPT-4o-mini)",
            "groq": "Llama-3.1 (Groq)",
        })
    )

# Cast numerics
num_like = [c for c in df.columns if any(k in c for k in
    ["latency","coverage","readability","citations","tokens","cost","Words","chars"])]
for c in num_like:
    df[c] = pd.to_numeric(df[c], errors="coerce")

st.dataframe(df, use_container_width=True, height=340)
section_divider()

# Aggregates
st.subheader("Aggregates")
c1, c2, c3 = st.columns(3)
with c1: st.metric("Total Runs", len(df))
with c2: st.metric("Modes Covered", df["mode"].nunique() if "mode" in df else 1)
with c3: st.metric("Votes Collected", int(df["preference"].notna().sum()) if "preference" in df else 0)

# Latency
if {"openai_latency","llama_latency"}.issubset(df.columns):
    st.subheader("Latency (s)")
    lat = df.melt(value_vars=["openai_latency","llama_latency"], var_name="model", value_name="seconds")
    lat["model"] = lat["model"].map({"openai_latency":"OpenAI (GPT-4o-mini)", "llama_latency":"Llama-3.1 (Groq)"})
    fig = px.box(lat, x="model", y="seconds", points="all")
    st.plotly_chart(fig, use_container_width=True)

# RAG: Coverage & Readability
rag_df = df[df["mode"].eq("rag")] if "mode" in df else pd.DataFrame()
if not rag_df.empty and {"coverage_openai","coverage_llama"}.issubset(rag_df.columns):
    st.subheader("Grounding Coverage (RAG)")
    cov = rag_df[["coverage_openai","coverage_llama"]].rename(columns={
        "coverage_openai":"OpenAI (GPT-4o-mini)",
        "coverage_llama":"Llama-3.1 (Groq)"
    }).melt(var_name="model", value_name="coverage")
    fig = px.violin(cov, x="model", y="coverage", box=True, points="all")
    st.plotly_chart(fig, use_container_width=True)

if not rag_df.empty and {"readability_openai","readability_llama"}.issubset(rag_df.columns):
    st.subheader("Readability (RAG)")
    rea = rag_df[["readability_openai","readability_llama"]].rename(columns={
        "readability_openai":"OpenAI (GPT-4o-mini)",
        "readability_llama":"Llama-3.1 (Groq)"
    }).melt(var_name="model", value_name="readability")
    fig = px.box(rea, x="model", y="readability", points="all")
    st.plotly_chart(fig, use_container_width=True)

# Votes
if "preference" in df.columns and not df["preference"].dropna().empty:
    st.subheader("User Votes")
    vc = (
        df["preference"]
        .fillna("—")
        .value_counts(dropna=False)
        .rename_axis("preference")
        .reset_index(name="count")
    )
    fig = px.bar(vc, x="preference", y="count", labels={"preference":"Vote","count":"Count"})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("No votes yet — submit a vote on compare pages.")

section_divider()
# Overall Verdict
st.subheader("Overall Verdict")

def safe_mean(s):
    s = pd.to_numeric(s, errors="coerce").dropna()
    return float(s.mean()) if len(s) else np.nan

metrics = {
    "lat_ai": safe_mean(df.get("openai_latency")),
    "lat_ll": safe_mean(df.get("llama_latency")),
    "cov_ai": safe_mean(rag_df.get("coverage_openai")) if not rag_df.empty else np.nan,
    "cov_ll": safe_mean(rag_df.get("coverage_llama")) if not rag_df.empty else np.nan,
    "rea_ai": safe_mean(rag_df.get("readability_openai")) if not rag_df.empty else np.nan,
    "rea_ll": safe_mean(rag_df.get("readability_llama")) if not rag_df.empty else np.nan,
}

if "preference" in df.columns:
    wins_ai = (df["preference"] == "OpenAI (GPT-4o-mini)").sum()
    wins_ll = (df["preference"] == "Llama-3.1 (Groq)").sum()
    total_v = max(1, (df["preference"].isin(["OpenAI (GPT-4o-mini)","Llama-3.1 (Groq)"])).sum())
    vote_ai = wins_ai / total_v
    vote_ll = wins_ll / total_v
else:
    vote_ai = vote_ll = np.nan

W = {"latency": 0.25, "coverage": 0.35, "readability": 0.20, "votes": 0.20}

def inv_norm(a, b):
    if np.isnan(a) or np.isnan(b): return (np.nan, np.nan)
    hi = max(a, b); lo = min(a, b); rng = hi - lo if hi != lo else 1.0
    return ((hi - a)/rng, (hi - b)/rng)  # lower better

def norm(a, b):
    if np.isnan(a) or np.isnan(b): return (np.nan, np.nan)
    hi = max(a, b); lo = min(a, b); rng = hi - lo if hi != lo else 1.0
    return ((a - lo)/rng, (b - lo)/rng)  # higher better

lat_ai, lat_ll = inv_norm(metrics["lat_ai"], metrics["lat_ll"])
cov_ai, cov_ll = norm(metrics["cov_ai"], metrics["cov_ll"]) if not np.isnan(metrics["cov_ai"]) and not np.isnan(metrics["cov_ll"]) else (np.nan, np.nan)
rea_ai, rea_ll = norm(metrics["rea_ai"], metrics["rea_ll"]) if not np.isnan(metrics["rea_ai"]) and not np.isnan(metrics["rea_ll"]) else (np.nan, np.nan)

def weighted(vals, weights):
    pairs = [(v, w) for v, w in zip(vals, weights) if not np.isnan(v)]
    if not pairs: return np.nan
    tw = sum(w for _, w in pairs)
    return sum(v*w for v, w in pairs) / (tw if tw else 1)

score_ai = weighted([lat_ai, cov_ai, rea_ai, vote_ai], [W["latency"],W["coverage"],W["readability"],W["votes"]])
score_ll = weighted([lat_ll, cov_ll, rea_ll, vote_ll], [W["latency"],W["coverage"],W["readability"],W["votes"]])

colA, colB = st.columns(2)
with colA: st.metric("OpenAI Score", f"{(score_ai*100):.1f}%" if not np.isnan(score_ai) else "—")
with colB: st.metric("Llama-3.1 Score", f"{(score_ll*100):.1f}%" if not np.isnan(score_ll) else "—")

if not np.isnan(score_ai) and not np.isnan(score_ll):
    if score_ai > score_ll:
        st.success("**Overall: OpenAI (GPT-4o-mini) leads** based on current runs.")
    elif score_ll > score_ai:
        st.success("**Overall: Llama-3.1 (Groq) leads** based on current runs.")
    else:
        st.info("**Overall: Tie** based on current runs.")
else:
    st.caption("Not enough comparable metrics yet to compute a verdict.")

# Persist current tracker rows to CSV (no overwrite of memory)
st.session_state.tracker.save_csv()

section_divider()
st.caption("Votes update the exact run via run_id and are saved immediately. If you still see 0, check the CSV is writable and that `tracker.update_by_id` exists.")
