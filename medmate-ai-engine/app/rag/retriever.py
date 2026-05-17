"""
RAG Retriever - BM25 + Vector Hybrid Search
Architecture: Elasticsearch (BM25) + Milvus (vector) -> EnsembleRetriever
"""
from typing import Optional
from dataclasses import dataclass

from pymilvus import Collection
from elasticsearch import Elasticsearch

from app.config import settings
from app.rag.knowledge_manager import knowledge_manager


@dataclass
class RetrievalResult:
    """Single retrieval result"""
    content: str
    source: str
    category: str
    score: float
    method: str  # "vector" or "bm25" or "hybrid"


class HybridRetriever:
    """
    BM25 + Vector hybrid retriever
    1. Vector search via Milvus (semantic similarity)
    2. BM25 search via Elasticsearch (keyword matching)
    3. Reciprocal Rank Fusion (RRF) to merge results
    """

    def __init__(self, vector_weight: float = 0.6, bm25_weight: float = 0.4):
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight

    def search(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        """
        Hybrid search: vector + BM25 -> RRF merge

        Args:
            query: user query text
            top_k: number of results to return

        Returns:
            List of RetrievalResult, sorted by RRF score
        """
        if not knowledge_manager.is_ready:
            return []

        # 1. Vector search
        vector_results = self._vector_search(query, top_k=top_k * 2)

        # 2. BM25 search
        bm25_results = self._bm25_search(query, top_k=top_k * 2)

        # 3. RRF fusion
        merged = self._rrf_merge(vector_results, bm25_results, top_k=top_k)

        return merged

    def _vector_search(self, query: str, top_k: int = 20) -> list[RetrievalResult]:
        """Search Milvus with query embedding"""
        try:
            query_vector = knowledge_manager.embed([query])[0]
            collection = knowledge_manager.milvus_collection

            results = collection.search(
                data=[query_vector],
                anns_field="vector",
                param={"metric_type": "COSINE", "params": {"ef": 128}},
                limit=top_k,
                output_fields=["content", "source", "category"],
            )

            return [
                RetrievalResult(
                    content=hit.entity.get("content", ""),
                    source=hit.entity.get("source", ""),
                    category=hit.entity.get("category", ""),
                    score=hit.score,
                    method="vector",
                )
                for hit in results[0]
            ]
        except Exception as e:
            print(f"[WARN] Vector search failed: {e}", flush=True)
            return []

    def _bm25_search(self, query: str, top_k: int = 20) -> list[RetrievalResult]:
        """Search Elasticsearch with BM25"""
        try:
            es = knowledge_manager.es_client
            response = es.search(
                index=settings.es_index,
                body={
                    "query": {
                        "match": {
                            "content": {
                                "query": query,
                                "analyzer": "standard",
                            }
                        }
                    },
                    "size": top_k,
                },
            )

            return [
                RetrievalResult(
                    content=hit["_source"]["content"],
                    source=hit["_source"].get("source", ""),
                    category=hit["_source"].get("category", ""),
                    score=hit["_score"],
                    method="bm25",
                )
                for hit in response["hits"]["hits"]
            ]
        except Exception as e:
            print(f"[WARN] BM25 search failed: {e}", flush=True)
            return []

    def _rrf_merge(
        self,
        vector_results: list[RetrievalResult],
        bm25_results: list[RetrievalResult],
        top_k: int = 10,
        k: int = 60,
    ) -> list[RetrievalResult]:
        """
        Reciprocal Rank Fusion (RRF)
        Score = sum( 1 / (k + rank_i) ) for each result list
        """
        scores: dict[str, float] = {}
        content_map: dict[str, RetrievalResult] = {}

        # Score from vector results
        for rank, result in enumerate(vector_results):
            key = result.content[:100]  # use content prefix as key
            rrf_score = self.vector_weight / (k + rank + 1)
            scores[key] = scores.get(key, 0) + rrf_score
            content_map[key] = result

        # Score from BM25 results
        for rank, result in enumerate(bm25_results):
            key = result.content[:100]
            rrf_score = self.bm25_weight / (k + rank + 1)
            scores[key] = scores.get(key, 0) + rrf_score
            if key not in content_map:
                content_map[key] = result

        # Sort by RRF score
        sorted_keys = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        results = []
        for key in sorted_keys[:top_k]:
            r = content_map[key]
            r.score = scores[key]
            r.method = "hybrid"
            results.append(r)

        return results


# Singleton
hybrid_retriever = HybridRetriever()
