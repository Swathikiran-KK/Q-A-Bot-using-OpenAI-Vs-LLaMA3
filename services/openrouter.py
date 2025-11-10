# services/openrouter.py
import base64, time, requests
from typing import Dict, List, Tuple, Optional
from utils.config import OPENROUTER_API_KEY, OPENROUTER_TEXT_MODEL, OPENROUTER_VISION_MODEL

URL = "https://openrouter.ai/api/v1/chat/completions"

class OpenRouterClient:
    def __init__(self, api_key: str = OPENROUTER_API_KEY):
        if not api_key:
            raise ValueError("Missing OPENROUTER_API_KEY")
        self.api_key = api_key

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "LLM Comparison Workbench"
        }

    def _run(self, model: str, messages: List[Dict], max_tokens: int = 512) -> Tuple[str, Dict, float]:
        t0 = time.time()
        resp = requests.post(URL, headers=self._headers(), json={
            "model": model, "messages": messages, "max_tokens": max_tokens
        }, timeout=60)
        t1 = time.time()
        try:
            resp.raise_for_status()
        except requests.HTTPError:
            raise ValueError(f"❌ OpenRouter request rejected. Model={model}. Response: {resp.text}")
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        latency = t1 - t0
        return content, usage, latency

    def chat_text(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        context: str = "",
        max_tokens: int = 512
    ):
        messages = [{"role": "system", "content": system}]
        if context:
            messages.append({"role": "user", "content": f"Context:\n{context}"})
        messages.append({"role": "user", "content": prompt})
        return self._run(OPENROUTER_TEXT_MODEL, messages, max_tokens)

    def chat_vision(
        self,
        prompt: str,
        images: List[bytes],
        system: str = "You are a helpful vision assistant.",
        max_tokens: int = 512,
        mime_types: Optional[List[str]] = None  # <-- supports PNG/JPG correctly
    ):
        parts = [{"type": "text", "text": prompt}]
        for i, img in enumerate(images):
            b64 = base64.b64encode(img).decode("utf-8")
            mt = (mime_types[i] if mime_types and i < len(mime_types) and mime_types[i] else "image/png")
            parts.append({"type": "image_url", "image_url": {"url": f"data:{mt};base64,{b64}"}})
        messages = [{"role": "system", "content": system}, {"role": "user", "content": parts}]
        return self._run(OPENROUTER_VISION_MODEL, messages, max_tokens)
