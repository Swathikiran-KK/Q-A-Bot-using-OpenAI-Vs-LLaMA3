import re, textstat
from typing import Dict

def token_estimate(text: str) -> int:
    return max(1, int(len(text)/4))  # ~4 chars/token heuristic

def cost_estimate(model_key_in: str, model_key_out: str, in_tokens: int, out_tokens: int, COST_MAP: Dict[str,float]) -> float:
    ci = COST_MAP.get(f"{model_key_in}:input", 0.0)
    co = COST_MAP.get(f"{model_key_out}:output", 0.0)
    return (in_tokens/1000.0)*ci + (out_tokens/1000.0)*co

def readability(text: str) -> float:
    try: return textstat.flesch_reading_ease(text)
    except Exception: return 0.0

def citation_count(text: str) -> int:
    return len(re.findall(r"\[\d+\]|\bhttps?://\S+", text))

def answer_length(text: str) -> int:
    return len(re.findall(r"\w+", text))

def grounding_coverage(answer: str, context: str) -> float:
    tok = lambda s: {w for w in re.findall(r"[a-zA-Z]{3,}", s.lower())}
    a, c = tok(answer), tok(context)
    if not a or not c: return 0.0
    return len(a & c) / len(a | c)
