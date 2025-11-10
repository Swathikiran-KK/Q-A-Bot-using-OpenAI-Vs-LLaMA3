import time, requests
from typing import Dict, List, Tuple
from utils.config import GROQ_API_KEY, GROQ_TEXT_MODEL

URL = "https://api.groq.com/openai/v1/chat/completions"

def _clip_for_tpm(s: str, max_tokens_est: int = 6000):
    # ~4 chars/token heuristic
    max_chars = max_tokens_est * 4
    return s[:max_chars]

class GroqClient:
    def __init__(self, api_key: str = GROQ_API_KEY):
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY")
        self.api_key = api_key

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def chat_text(self, prompt: str, system: str = "You are a helpful assistant.", context: str = "", max_tokens: int = 512) -> Tuple[str, Dict, float]:
        # clip to avoid TPM errors
        prompt = _clip_for_tpm(prompt)
        context = _clip_for_tpm(context)

        messages = [{"role": "system", "content": system}]
        if context:
            messages.append({"role": "user", "content": f"Context:\n{context}"})
        messages.append({"role": "user", "content": prompt})

        t0 = time.time()
        resp = requests.post(URL, headers=self._headers(), json={
            "model": GROQ_TEXT_MODEL, "messages": messages, "max_tokens": max_tokens
        }, timeout=60)
        t1 = time.time()

        if not resp.ok:
            # Make the most common issues actionable
            raise ValueError(
                f"❌ Groq request rejected. Model={GROQ_TEXT_MODEL}. → Check GROQ_TEXT_MODEL and payload. "
                f"Response: {resp.text}"
            )

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        latency = t1 - t0
        return content, usage, latency
