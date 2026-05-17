"""
模型抽象基类 - 基于 LangChain BaseChatModel
所有模型 Provider 统一使用 LangChain 接口
"""
from abc import ABC, abstractmethod
from langchain_core.language_models import BaseChatModel


class BaseModelProvider(ABC):
    """模型提供者抽象基类"""

    @abstractmethod
    def get_llm(self) -> BaseChatModel:
        """获取 LangChain LLM 实例"""
        ...

    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        ...
