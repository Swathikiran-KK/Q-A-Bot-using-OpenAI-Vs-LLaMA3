import streamlit as st
from components.ui import page_header, metric_cards, section_divider, answer
from services.openrouter import OpenRouterClient
from services.groq_llama import GroqClient
from evaluators.metrics import token_estimate, cost_estimate, readability, citation_count, answer_length
from analytics.tracker import MetricsTracker
from utils.config import COST_MAP

# ---- helper: radio fallback for older Streamlit
def safe_vote_radio(label: str, key: str):
    try:
        return st.radio(label,
                        ["OpenAI (GPT-4o-mini)", "Llama-3.1 (Groq)", "Tie"],
                        horizontal=True, index=None, key=key)
    except TypeError:
        val = st.selectbox(label,
                           ["(choose…)", "OpenAI (GPT-4o-mini)", "Llama-3.1 (Groq)", "Tie"],
                           key=key, index=0)
        return None if val == "(choose…)" else val

# Ensure tracker
if "tracker" not in st.session_state:
    st.session_state.tracker = MetricsTracker()

# Local state bucket for this page
if "text_last" not in st.session_state:
    st.session_state.text_last = None   # will store dict with run_id and outputs

st.set_page_config(page_title="Text Compare", page_icon="📝", layout="wide")
page_header("Text Compare", "Side-by-side metrics", "Text")

with st.expander("Prompt", expanded=True):
    prompt = st.text_area("Your prompt", height=140, placeholder="Explain transformers to a 10-year-old.")
with st.expander("Advanced"):
    system = st.text_area("System prompt", value="You are a helpful, concise assistant.")
    max_tokens = st.slider("Max tokens", 128, 2048, 512, 64)

do_run = st.button("Run Comparison", type="primary", use_container_width=True, disabled=not prompt.strip())
section_divider()

# When user clicks run, compute and store results in session_state, then render below
if do_run:
    orc, grq = OpenRouterClient(), GroqClient()
    with st.spinner("Calling models..."):
        ai_text, ai_usage, ai_lat = orc.chat_text(prompt, system=system, max_tokens=max_tokens)
        ll_text, ll_usage, ll_lat = grq.chat_text(prompt, system=system, max_tokens=max_tokens)

    ai_in = ai_usage.get("prompt_tokens", token_estimate(prompt+system))
    ai_out = ai_usage.get("completion_tokens", token_estimate(ai_text))
    ll_in = ll_usage.get("prompt_tokens", token_estimate(prompt+system))
    ll_out = ll_usage.get("completion_tokens", token_estimate(ll_text))
    ai_cost = cost_estimate("openai/gpt-4o-mini","openai/gpt-4o-mini",ai_in,ai_out,COST_MAP)
    ll_cost = cost_estimate("llama-3.1-8b-instant","llama-3.1-8b-instant",ll_in,ll_out,COST_MAP)

    # log now and persist
    run_id = st.session_state.tracker.log({
        "mode":"text","prompt":prompt,
        "openai_answer":ai_text,"llama_answer":ll_text,
        "openai_latency":ai_lat,"llama_latency":ll_lat,
        "openai_tokens_in":ai_in,"openai_tokens_out":ai_out,
        "llama_tokens_in":ll_in,"llama_tokens_out":ll_out,
        "openai_cost":ai_cost,"llama_cost":ll_cost,
        "preference": None
    })
    st.session_state.tracker.save_csv()

    # stash everything to render consistently after rerun
    st.session_state.text_last = dict(
        run_id=run_id, prompt=prompt,
        ai_text=ai_text, ll_text=ll_text,
        ai_lat=ai_lat, ll_lat=ll_lat,
        ai_in=ai_in, ai_out=ai_out, ll_in=ll_in, ll_out=ll_out,
        ai_cost=ai_cost, ll_cost=ll_cost
    )

# Always render from state if available
if st.session_state.text_last:
    S = st.session_state.text_last
    metric_cards(
        {"Latency (s)": f"{S['ai_lat']:.2f}", "Tokens (in/out)": f"{S['ai_in']}/{S['ai_out']}",
         "Cost ($)": f"{S['ai_cost']:.4f}", "Readability": f"{readability(S['ai_text']):.1f}",
         "Length": f"{answer_length(S['ai_text'])}", "Citations": f"{citation_count(S['ai_text'])}"},
        {"Latency (s)": f"{S['ll_lat']:.2f}", "Tokens (in/out)": f"{S['ll_in']}/{S['ll_out']}",
         "Cost ($)": f"{S['ll_cost']:.4f}", "Readability": f"{readability(S['ll_text']):.1f}",
         "Length": f"{answer_length(S['ll_text'])}", "Citations": f"{citation_count(S['ll_text'])}"},
        "OpenAI (GPT-4o-mini)", "Llama-3.1 (Groq)"
    )
    section_divider()
    c1, c2 = st.columns(2)
    with c1: answer("OpenAI", S['ai_text'])
    with c2: answer("Llama-3.1", S['ll_text'])

    section_divider()
    with st.form("vote_text_form", clear_on_submit=True):
        vote = safe_vote_radio("Which answer do you prefer?", "vote_text_choice")
        submitted = st.form_submit_button("Save Vote")
        if submitted:
            if S['run_id'] is not None:
                st.session_state.tracker.update_by_id(S['run_id'], preference=vote or "Tie")
                st.session_state.tracker.save_csv()
                st.success(f"Saved vote for run #{S['run_id']}: {vote or 'Tie'}")
            else:
                st.error("Could not find the run to attach this vote.")
