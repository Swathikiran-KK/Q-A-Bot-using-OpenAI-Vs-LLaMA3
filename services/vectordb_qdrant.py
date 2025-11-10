from typing import List, Dict, Optional, Tuple
import uuid
from utils.config import QDRANT_URL, QDRANT_API_KEY, JINA_API_KEY
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from services.embeddings_jina import JinaEmbeddings, JINA_DIM

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class VectorDB:
    """
    If Qdrant + Jina keys exist → hosted vector search.
    Else → local TF-IDF matrix (no network).
    """
    def __init__(self, collection="benchmark_chunks"):
        self.collection = collection
        self.hosted = bool(QDRANT_URL and QDRANT_API_KEY and JINA_API_KEY)
        if self.hosted:
            self.client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=30)
            cols = {c.name for c in self.client.get_collections().collections}
            if self.collection not in cols:
                self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=qm.VectorParams(size=JINA_DIM, distance=qm.Distance.COSINE)
                )
            self.embedder = JinaEmbeddings()
        else:
            self.docs: List[Dict] = []
            self.vec = TfidfVectorizer(ngram_range=(1,2), strip_accents="unicode", lowercase=True)
            self.mat = None

    def clear(self):
        if self.hosted:
            try:
                self.client.delete_collection(self.collection)
            except Exception:
                pass
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=qm.VectorParams(size=JINA_DIM, distance=qm.Distance.COSINE)
            )
        else:
            self.docs = []
            self.mat = None

    def add_chunks(self, chunks: List[Dict]):
        """
        chunks: [{"text": str, "metadata": {...}}]
        """
        if not chunks: return
        texts = [c["text"] for c in chunks]
        if self.hosted:
            vecs = self.embedder.embed(texts)
            pts = []
            for vec, c in zip(vecs, chunks):
                pts.append(qm.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=[float(x) for x in vec],
                    payload={"text": c["text"], **(c.get("metadata") or {})}
                ))
            self.client.upsert(collection_name=self.collection, points=pts)
        else:
            # Local TF-IDF
            self.docs.extend(chunks)
            self.mat = self.vec.fit_transform([d["text"] for d in self.docs])

    def search_with_scores(self, query: str, k: int = 6) -> List[Tuple[str, float, Dict]]:
        """
        Returns list of (text, score, payload/metadata)
        """
        if not query.strip(): return []
        if self.hosted:
            qv = self.embedder.embed([query])[0]
            res = self.client.search(
                collection_name=self.collection,
                query_vector=qv, limit=k, with_payload=True, score_threshold=None
            )
            out = []
            for r in res:
                payload = r.payload or {}
                out.append((payload.get("text", ""), float(r.score), payload))
            return out
        else:
            if not self.docs: return []
            qv = self.vec.transform([query])
            sims = cosine_similarity(qv, self.mat)[0]
            idxs = sims.argsort()[::-1][:k]
            out = []
            for i in idxs:
                out.append((self.docs[i]["text"], float(sims[i]), self.docs[i].get("metadata", {})))
            return out
