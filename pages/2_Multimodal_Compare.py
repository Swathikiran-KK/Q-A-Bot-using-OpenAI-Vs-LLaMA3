import streamlit as st
from components.ui import page_header, metric_cards, section_divider, answer
from services.openrouter import OpenRouterClient
from services.groq_llama import GroqClient
from retrieval.document_processor import extract_text_from_pdf, extract_text_from_docx, extract_text_from_csv
from evaluators.metrics import token_estimate, readability, citation_count, answer_length
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

if "tracker" not in st.session_state:
    st.session_state.tracker = MetricsTracker()

# Keep last runs for both modes so voting survives reruns
if "image_last" not in st.session_state:
    st.session_state.image_last = None
if "doc_last" not in st.session_state:
    st.session_state.doc_last = None

st.set_page_config(page_title="Images & Docs", page_icon="🖼️", layout="wide")
page_header("Images & Documents",
            "OpenAI (Vision) vs Llama-3.1 (text); and Documents → Text",
            "Multimodal")

mode = st.radio("Mode", ["Image → Text", "Document → Text"], horizontal=True)

orc, grq = OpenRouterClient(), GroqClient()

# ---------- Image → Text ----------
if mode == "Image → Text":
    c1, c2 = st.columns([0.45, 0.55])
    with c1:
        img = st.file_uploader("Upload an image (PNG/JPG)", type=["png","jpg","jpeg"])
        prompt = st.text_input("Prompt", value="Describe this image in detail.")
        do_run = st.button("Run", type="primary", use_container_width=True, disabled=not img)
        if img: st.image(img, use_container_width=True, caption="Input image")

    if img and do_run:
        image_bytes = img.read()
        mime = img.type or "image/png"
        with st.spinner("Calling models..."):
            ai_ans, ai_usage, ai_lat = orc.chat_vision(prompt, [image_bytes], mime_types=[mime])
            ll_ans, ll_usage, ll_lat = grq.chat_text(prompt + "\n(Note: image not visible to this model.)")

        ai_in = ai_usage.get("prompt_tokens", token_estimate(prompt))
        ai_out = ai_usage.get("completion_tokens", token_estimate(ai_ans))
        ll_in = ll_usage.get("prompt_tokens", token_estimate(prompt))
        ll_out = ll_usage.get("completion_tokens", token_estimate(ll_ans))

        run_id = st.session_state.tracker.log({
            "mode": "image",
            "prompt": prompt,
            "filename": getattr(img, "name", ""),
            "openai_answer": ai_ans, "llama_answer": ll_ans,
            "openai_latency": ai_lat, "llama_latency": ll_lat,
            "openai_tokens_in": ai_in, "openai_tokens_out": ai_out,
            "llama_tokens_in": ll_in, "llama_tokens_out": ll_out,
            "preference": None
        })
        st.session_state.tracker.save_csv()

        st.session_state.image_last = dict(
            run_id=run_id, prompt=prompt, filename=getattr(img, "name", ""),
            ai_ans=ai_ans, ll_ans=ll_ans,
            ai_lat=ai_lat, ll_lat=ll_lat,
            ai_in=ai_in, ai_out=ai_out, ll_in=ll_in, ll_out=ll_out
        )

    # render from state if we have a last image run
    if st.session_state.image_last:
        S = st.session_state.image_last
        metric_cards(
            {"Latency (s)": f"{S['ai_lat']:.2f}", "Tokens (in/out)": f"{S['ai_in']}/{S['ai_out']}",
             "Readability": f"{readability(S['ai_ans']):.1f}", "Length": f"{answer_length(S['ai_ans'])}",
             "Citations": f"{citation_count(S['ai_ans'])}"},
            {"Latency (s)": f"{S['ll_lat']:.2f}", "Tokens (in/out)": f"{S['ll_in']}/{S['ll_out']}",
             "Readability": f"{readability(S['ll_ans']):.1f}", "Length": f"{answer_length(S['ll_ans'])}",
             "Citations": f"{citation_count(S['ll_ans'])}"},
            "OpenAI Vision (GPT-4o-mini)", "Llama-3.1 (text baseline)"
        )
        section_divider()
        cA, cB = st.columns(2)
        with cA: answer("OpenAI (Vision) Answer", S['ai_ans'])
        with cB: answer("Llama-3.1 (Text) Answer", S['ll_ans'])

        section_divider()
        with st.form("vote_img_form", clear_on_submit=True):
            vote = safe_vote_radio("Which answer do you prefer?", "vote_img_choice")
            submitted = st.form_submit_button("Save Vote")
            if submitted:
                if S['run_id'] is not None:
                    st.session_state.tracker.update_by_id(S['run_id'], preference=vote or "Tie")
                    st.session_state.tracker.save_csv()
                    st.success(f"Saved vote for run #{S['run_id']}: {vote or 'Tie'}")
                else:
                    st.error("Could not find the run to attach this vote.")

# ---------- Document → Text ----------
else:
    with st.expander("Upload a document"):
        f = st.file_uploader("PDF, DOCX, CSV, or TXT", type=["pdf","docx","csv","txt"])
    prompt = st.text_area("Your question or instruction",
                          placeholder="Summarize this document in bullet points.")
    do_run = st.button("Run on Document", type="primary", use_container_width=True,
                       disabled=not (f and prompt.strip()))
    section_divider()

    if f and do_run:
        ext = (f.name.split(".")[-1] or "").lower()
        text = ""
        if ext == "pdf":
            text = extract_text_from_pdf(f)
        elif ext == "docx":
            text = extract_text_from_docx(f.read())
        elif ext == "csv":
            text = extract_text_from_csv(f.read())
        elif ext == "txt":
            text = f.read().decode("utf-8", errors="ignore")
        else:
            st.error("Unsupported file type."); st.stop()

        if not text.strip():
            st.warning("No selectable text found. If this is a scanned PDF, run OCR first.")
        else:
            combined_prompt = f"Document:\n{text[:12000]}\n\nInstruction:\n{prompt}"
            with st.spinner("Calling models..."):
                ai_ans, ai_usage, ai_lat = orc.chat_text(combined_prompt)
                ll_ans, ll_usage, ll_lat = grq.chat_text(combined_prompt)

            ai_in = ai_usage.get("prompt_tokens", token_estimate(combined_prompt))
            ai_out = ai_usage.get("completion_tokens", token_estimate(ai_ans))
            ll_in = ll_usage.get("prompt_tokens", token_estimate(combined_prompt))
            ll_out = ll_usage.get("completion_tokens", token_estimate(ll_ans))

            run_id = st.session_state.tracker.log({
                "mode": "doc",
                "prompt": prompt,
                "filename": getattr(f, "name", ""),
                "openai_answer": ai_ans, "llama_answer": ll_ans,
                "openai_latency": ai_lat, "llama_latency": ll_lat,
                "openai_tokens_in": ai_in, "openai_tokens_out": ai_out,
                "llama_tokens_in": ll_in, "llama_tokens_out": ll_out,
                "preference": None
            })
            st.session_state.tracker.save_csv()

            st.session_state.doc_last = dict(
                run_id=run_id, prompt=prompt, filename=getattr(f, "name", ""),
                ai_ans=ai_ans, ll_ans=ll_ans,
                ai_lat=ai_lat, ll_lat=ll_lat,
                ai_in=ai_in, ai_out=ai_out, ll_in=ll_in, ll_out=ll_out
            )

    # Render last doc run (if exists)
    if st.session_state.doc_last:
        S = st.session_state.doc_last
        metric_cards(
            {"Latency (s)": f"{S['ai_lat']:.2f}", "Tokens (in/out)": f"{S['ai_in']}/{S['ai_out']}",
             "Readability": f"{readability(S['ai_ans']):.1f}", "Length": f"{answer_length(S['ai_ans'])}",
             "Citations": f"{citation_count(S['ai_ans'])}"},
            {"Latency (s)": f"{S['ll_lat']:.2f}", "Tokens (in/out)": f"{S['ll_in']}/{S['ll_out']}",
             "Readability": f"{readability(S['ll_ans']):.1f}", "Length": f"{answer_length(S['ll_ans'])}",
             "Citations": f"{citation_count(S['ll_ans'])}"},
            "OpenAI (GPT-4o-mini)", "Llama-3.1 (Groq)"
        )
        section_divider()
        c1, c2 = st.columns(2)
        with c1: answer("OpenAI Answer", S['ai_ans'])
        with c2: answer("Llama-3.1 Answer", S['ll_ans'])

        section_divider()
        with st.form("vote_doc_form", clear_on_submit=True):
            vote = safe_vote_radio("Which answer do you prefer?", "vote_doc_choice")
            submitted = st.form_submit_button("Save Vote")
            if submitted:
                if S['run_id'] is not None:
                    st.session_state.tracker.update_by_id(S['run_id'], preference=vote or "Tie")
                    st.session_state.tracker.save_csv()
                    st.success(f"Saved vote for run #{S['run_id']}: {vote or 'Tie'}")
                else:
                    st.error("Could not find the run to attach this vote.")
