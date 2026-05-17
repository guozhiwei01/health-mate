"""
BGE-M3 Reranker
Rerank retrieval results for better precision
Uses cross-encoder scoring to refine the top-k results
"""
from app.rag.retriever import RetrievalResult
from app.rag.knowledge_manager import knowledge_manager


class BGEReranker:
    """BGE-M3 based reranker using cross-encoder scoring"""

    def __init__(self, top_k: int = 5):
        self.top_k = top_k

    def rerank(self, query: str, results: list[RetrievalResult]) -> list[RetrievalResult]:
        """
        Rerank results using BGE-M3 embedding similarity as proxy
        Full cross-encoder reranking requires bge-reranker-v2 (future upgrade)

        Args:
            query: user query
            results: candidate results from hybrid retriever

        Returns:
            top_k reranked results
        """
        if not results or not knowledge_manager.is_ready:
            return results[:self.top_k]

        # Embed query and all candidates
        texts = [query] + [r.content for r in results]
        embeddings = knowledge_manager.embed(texts)

        query_emb = embeddings[0]
        candidate_embs = embeddings[1:]

        # Compute cosine similarity
        scored = []
        for i, (result, cand_emb) in enumerate(zip(results, candidate_embs)):
            sim = self._cosine_sim(query_emb, cand_emb)
            result.score = sim
            scored.append(result)

        # Sort by reranker score
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:self.top_k]

    @staticmethod
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        """Cosine similarity between two vectors"""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x ** 2 for x in a) ** 0.5
        norm_b = sum(x ** 2 for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


# Singleton
bge_reranker = BGEReranker(top_k=5)
