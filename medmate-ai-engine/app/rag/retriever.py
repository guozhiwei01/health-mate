"""
混合检索器
BM25（ES, 权重 0.3）+ 向量检索（Milvus, 权重 0.7）
"""


class HybridRetriever:
    """混合检索器"""

    def __init__(self, bm25_weight: float = 0.3, vector_weight: float = 0.7):
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight

    async def retrieve(self, query: str, top_k: int = 10) -> list:
        """
        混合检索

        Args:
            query: 检索查询
            top_k: 返回数量

        Returns:
            list of {"text": str, "score": float, "source": str}
        """
        # TODO: Week 7 实现
        # 1. ES BM25 检索
        # 2. Milvus 向量检索
        # 3. 加权融合 + 去重
        return []
