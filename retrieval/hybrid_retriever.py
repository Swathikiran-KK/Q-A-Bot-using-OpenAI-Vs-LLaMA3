from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class HybridRetriever:
    def __init__(self, chunks):
        self.chunks = chunks or []
        self.corpus = [c["text"] for c in self.chunks]
        self.bm25 = BM25Okapi([c.split() for c in self.corpus]) if self.corpus else None
        self.vec = TfidfVectorizer(ngram_range=(1,2), strip_accents="unicode")
        self.mat = self.vec.fit_transform(self.corpus) if self.corpus else None

    def get_top_chunks(self, query, k=5):
        if not self.corpus or not query.strip(): return []
        b_scores = self.bm25.get_scores(query.split())
        qv = self.vec.transform([query]); t_scores = cosine_similarity(qv, self.mat)[0]
        def norm(a): a=np.array(a,dtype=float); lo,hi=a.min(),a.max(); return (a-lo)/(hi-lo+1e-9)
        bn, tn = norm(b_scores), norm(t_scores)
        cand = list(dict.fromkeys(np.argsort(-b_scores)[:max(k,10)].tolist() + np.argsort(-t_scores)[:max(k,10)].tolist()))
        blended = sorted([(i, 0.5*bn[i]+0.5*tn[i]) for i in cand], key=lambda x:-x[1])[:k]
        return [self.chunks[i] for i,_ in blended]
