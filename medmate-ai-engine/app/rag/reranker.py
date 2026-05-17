"""
BGE-M3 Reranker - 精排
对混合检索结果进行二次排序，取 Top-5
"""


class BGEReranker:
    """BGE-M3 Reranker"""

    def __init__(self):
        self.model = None

    def load(self):
        """加载 Reranker 模型"""
        # TODO: Week 7 实现
        # from sentence_transformers import CrossEncoder
        # self.model = CrossEncoder("BAAI/bge-m3", ...)
        pass

    async def rerank(self, query: str, documents: list, top_k: int = 5) -> list:
        """
        精排

        Args:
            query: 用户查询
            documents: 候选文档列表
            top_k: 返回 Top-K

        Returns:
            重排后的文档列表
        """
        # TODO: Week 7 实现
        return documents[:top_k]


# 全局单例
reranker = BGEReranker()
