"""
深度通道模型 - HealthMate-Med LangChain Provider
自动适配 DashScope（阿里云百炼）和 Ollama（本地微调模型）
"""
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

from app.models.base import BaseModelProvider
from app.config import settings


MEDICAL_SYSTEM_PROMPT = """你是 HealthMate-Med，一个经过医疗数据微调的专业健康助手。

职责：
1. 根据用户描述的症状，进行系统性追问（OPQRST 问诊法）
2. 提供用药建议时，必须说明适应症、禁忌、副作用
3. 遇到紧急情况，必须第一时间建议就医
4. 不做确诊，只提供参考建议

安全规则：
- 始终提醒"以上建议仅供参考，具体请咨询医生"
- 涉及处方药时，提醒需要医生处方
- 检测到自残/自杀倾向时，提供心理援助热线"""


class HealthMateMedProvider(BaseModelProvider):
    """
    深度通道：医疗专业模型
    - DashScope 模式：调用 qwen3-flash（云端）
    - Ollama 模式：调用本地微调的 healthmate-med
    """

    def __init__(self):
        self._llm = ChatOpenAI(
            model=settings.active_med_model,
            base_url=settings.active_base_url,
            api_key=settings.active_api_key,
            temperature=0.3,  # 医疗场景低温度，减少幻觉
            max_tokens=2048,
            streaming=True,
        )

    def get_llm(self) -> BaseChatModel:
        """获取 LangChain LLM 实例"""
        return self._llm

    def get_system_prompt(self) -> str:
        return MEDICAL_SYSTEM_PROMPT


# 全局单例
healthmate_med = HealthMateMedProvider()
