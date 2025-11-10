import streamlit as st
from components.ui import page_header, section_divider, metric_cards, answer
from retrieval.document_processor import extract_text_from_pdf, chunk_text
from retrieval.hybrid_retriever import HybridRetriever
from services.vectordb_qdrant import VectorDB
from services.openrouter import OpenRouterClient
from services.groq_llama import GroqClient
from evaluators.metrics import grounding_coverage, readability, citation_count, answer_length
from analytics.tracker import MetricsTracker

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

st.set_page_config(page_title="RAG Compare", page_icon="📚", layout="wide")
page_header("RAG Compare", "Ask grounded questions over a PDF", "Retrieval")

if "tracker" not in st.session_state:
    st.session_state.tracker = MetricsTracker()
if "chunks" not in st.session_state:
    st.session_state.chunks = []
if "rag_last" not in st.session_state:
    st.session_state.rag_last = None

with st.expander("Document"):
    pdf = st.file_uploader("Upload a PDF", type="pdf")
    if pdf and st.button("Index", use_container_width=True):
        text = extract_text_from_pdf(pdf)
        if not text.strip():
            st.warning("No selectable text found (maybe scanned?). Try OCR first.")
        else:
            st.session_state.chunks = chunk_text(text, chunk_size=900, overlap=120)
            st.success(f"Chunked into {len(st.session_state.chunks)} segments.")

if not st.session_state.chunks:
    st.info("Upload & index a PDF to enable RAG.")
    st.stop()

retriever = HybridRetriever(st.session_state.chunks)
vdb = VectorDB(); vdb.clear(); vdb.add_chunks(st.session_state.chunks)

q = st.text_input("Ask a question grounded in the document")
k = st.slider("Top-K context (after blend)", 3, 12, 6)
w_vec = st.slider("Vector weighting (0→BM25/TF-IDF, 1→Vector)", 0.0, 1.0, 0.5, 0.05)

do_run = st.button("Compare Answers", type="primary", disabled=not q.strip())

if do_run:
    # BM25/TF-IDF
    bm_chunks = retriever.get_top_chunks(q, k=max(k, 8))
    bm_texts = [c["text"] for c in bm_chunks]
    bm_index = {t: i for i, t in enumerate(bm_texts)}

    # Vector
    vec_hits = vdb.search_with_scores(q, k=max(k, 8))
    vec_texts = [t for (t, s, _) in vec_hits]
    vec_scores = {t: s for (t, s, _) in vec_hits}

    # Normalize & blend
    def normalize(d: dict):
        if not d: return {}
        vals = list(d.values()); lo, hi = min(vals), max(vals)
        if hi - lo < 1e-9: return {k: 0.0 for k in d}
        return {k: (v - lo) / (hi - lo + 1e-9) for k, v in d.items()}

    bm_scores = normalize({t: (len(bm_texts) - idx) for t, idx in bm_index.items()})
    vs = normalize(vec_scores)
    union = list(dict.fromkeys(bm_texts + vec_texts))
    blended = sorted(
        [(t, (1 - w_vec) * bm_scores.get(t, 0.0) + w_vec * vs.get(t, 0.0)) for t in union],
        key=lambda x: -x[1]
    )
    top_context_texts = [t for t, _ in blended[:k]]

    # Citations
    idx_map = {c["text"]: i for i, c in enumerate(st.session_state.chunks)}
    citations = [idx_map.get(t, -1) for t in top_context_texts]
    context = ""
    for i, t in zip(citations, top_context_texts):
        label = f"[{i}]" if i >= 0 else "[?]"
        context += f"{label} {t}\n\n"

    # Call models
    orc, grq = OpenRouterClient(), GroqClient()
    with st.spinner("Calling models..."):
        sys = "Answer using only the provided context. If unknown, say you don't know. Include inline citation labels like [12] if applicable."
        ai_ans, _, ai_lat = orc.chat_text(q, context=context, system=sys)
        ll_ans, _, ll_lat = grq.chat_text(q, context=context, system=sys)

    # log & persist
    run_id = st.session_state.tracker.log({
        "mode": "rag",
        "prompt": q,
        "k": k,
        "vector_weight": w_vec,
        "context_chars": len(context),
        "openai_answer": ai_ans, "llama_answer": ll_ans,
        "openai_latency": ai_lat, "llama_latency": ll_lat,
        "coverage_openai": grounding_coverage(ai_ans, context),
        "coverage_llama": grounding_coverage(ll_ans, context),
        "readability_openai": readability(ai_ans),
        "readability_llama": readability(ll_ans),
        "citations_openai": citation_count(ai_ans),
        "citations_llama": citation_count(ll_ans),
        "preference": None
    })
    st.session_state.tracker.save_csv()

    # stash for reliable rendering & voting
    st.session_state.rag_last = dict(
        run_id=run_id, q=q, k=k, w_vec=w_vec, context=context,
        ai_ans=ai_ans, ll_ans=ll_ans,
        ai_lat=ai_lat, ll_lat=ll_lat
    )

# Always render from state if available
if st.session_state.rag_last:
    S = st.session_state.rag_last
    st.subheader("Context (blended)")
    st.code(S['context'][:3000] + ("..." if len(S['context']) > 3000 else ""))

    metric_cards(
        {"Coverage": f"{grounding_coverage(S['ai_ans'], S['context']):.2f}",
         "Readability": f"{readability(S['ai_ans']):.1f}",
         "Citations": f"{citation_count(S['ai_ans'])}",
         "Words": f"{answer_length(S['ai_ans'])}",
         "Latency (s)": f"{S['ai_lat']:.2f}"},
        {"Coverage": f"{grounding_coverage(S['ll_ans'], S['context']):.2f}",
         "Readability": f"{readability(S['ll_ans']):.1f}",
         "Citations": f"{citation_count(S['ll_ans'])}",
         "Words": f"{answer_length(S['ll_ans'])}",
         "Latency (s)": f"{S['ll_lat']:.2f}"},
        "OpenAI (GPT-4o-mini)", "Llama-3.1 (Groq)"
    )

    c1, c2 = st.columns(2)
    with c1: answer("OpenAI", S['ai_ans'])
    with c2: answer("Llama-3.1", S['ll_ans'])

    section_divider()
    with st.form("vote_rag_form", clear_on_submit=True):
        vote = safe_vote_radio("Which answer do you prefer?", "vote_rag_choice")
        submitted = st.form_submit_button("Save Vote")
        if submitted:
            if S['run_id'] is not None:
                st.session_state.tracker.update_by_id(S['run_id'], preference=vote or "Tie")
                st.session_state.tracker.save_csv()
                st.success(f"Saved vote for run #{S['run_id']}: {vote or 'Tie'}")
            else:
                st.error("Could not find the run to attach this vote.")
