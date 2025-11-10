import requests
from utils.config import JINA_API_KEY

JINA_URL = "https://api.jina.ai/v1/embeddings"
JINA_MODEL = "jina-embeddings-v3"
JINA_DIM = 1024

class JinaEmbeddings:
    def __init__(self, api_key: str = JINA_API_KEY, model: str = JINA_MODEL):
        if not api_key:
            raise ValueError("Missing JINA_API_KEY")
        self.api_key = api_key
        self.model = model

    def embed(self, texts):
        r = requests.post(JINA_URL, headers={
            "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"
        }, json={"input": texts, "model": self.model}, timeout=60)
        r.raise_for_status()
        data = r.json()["data"]
        data = sorted(data, key=lambda x: x["index"])
        return [d["embedding"] for d in data]
