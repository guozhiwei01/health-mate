"""
医学知识库管理
- 文档导入、切分、向量化
- 增量更新走异步管线
"""
from app.config import settings


class MedicalKnowledgeBase:
    """医学知识库管理器"""

    def __init__(self):
        self.milvus_client = None
        self.es_client = None

    async def init(self):
        """初始化连接"""
        # TODO: Week 7 实现
        # 连接 Milvus + ES
        pass

    async def add_document(self, doc_path: str, metadata: dict = None):
        """
        添加文档到知识库
        流程：读取 → 切分 → Embedding → 写入 Milvus + ES
        """
        # TODO: Week 7 实现
        pass

    async def search(self, query: str, top_k: int = 5) -> list:
        """
        混合检索
        BM25（ES, 权重 0.3）+ 向量检索（Milvus, 权重 0.7）→ Reranker Top-K
        """
        # TODO: Week 7 实现
        return []

    async def close(self):
        """关闭连接"""
        pass


# 全局单例
medical_kb = MedicalKnowledgeBase()
