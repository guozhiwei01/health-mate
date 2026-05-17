"""
快速通道模型 - LangChain ChatOpenAI Provider
自动适配 DashScope（阿里云百炼）和 Ollama（本地推理）
"""
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

from app.models.base import BaseModelProvider
from app.config import settings


FAST_SYSTEM_PROMPT = "你是 HealthMate，一个专业的健康助手。请用通俗易懂的语言回答健康相关问题。"


class QwenFastProvider(BaseModelProvider):
    """
    快速通道：轻量模型
    - DashScope 模式：调用 qwen3-flash（云端）
    - Ollama 模式：调用本地 qwen2.5:7b
    """

    def __init__(self):
        self._llm = ChatOpenAI(
            model=settings.active_fast_model,
            base_url=settings.active_base_url,
            api_key=settings.active_api_key,
            temperature=0.7,
            max_tokens=1024,
            streaming=True,  # 默认开启流式
        )

    def get_llm(self) -> BaseChatModel:
        """获取 LangChain LLM 实例"""
        return self._llm

    def get_system_prompt(self) -> str:
        return FAST_SYSTEM_PROMPT


# 全局单例
qwen_fast = QwenFastProvider()
