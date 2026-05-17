"""
医学文档切分策略
- 优先按语义单元切分：章节 > 段落 > 句子
- 化验单/表格保留完整，不切分
"""


class MedicalChunker:
    """医学文档切分器"""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, text: str, doc_type: str = "text") -> list[dict]:
        """
        切分文档

        Args:
            text: 文档文本
            doc_type: 文档类型 ("text" / "table" / "report")

        Returns:
            list of {"text": str, "metadata": dict}
        """
        # TODO: Week 7 实现
        # 使用 RecursiveCharacterTextSplitter
        # separators=["\\n## ", "\\n### ", "\\n\\n", "\\n", "。"]
        return [{"text": text, "metadata": {"type": doc_type}}]
