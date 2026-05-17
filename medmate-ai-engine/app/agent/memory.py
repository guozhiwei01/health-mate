"""
上下文压缩策略 - 医疗安全设计
超过 10 轮后采用结构化提取 + 保留关键轮
"""
from pydantic import BaseModel


class MedicalContextSummary(BaseModel):
    """结构化医疗上下文摘要"""
    chief_complaint: str = ""              # 主诉："头痛两天"
    symptoms: list[str] = []               # 已确认症状
    denied_symptoms: list[str] = []        # 明确否认的症状（"没有恶心"）
    medications: list[str] = []            # 当前用药
    allergies: list[str] = []              # 过敏史
    key_turn_indices: list[int] = []       # 保留原文的关键轮次
    summary_text: str = ""                 # 给模型看的文本摘要


# 关键轮判断关键词
KEY_TURN_KEYWORDS = ["症状", "不舒服", "疼", "吃", "药", "过敏", "没有", "否认"]


def is_key_turn(turn: dict) -> bool:
    """判断是否为关键轮次（包含新症状、否认症状、用药信息）"""
    content = turn.get("content", "")
    return any(kw in content for kw in KEY_TURN_KEYWORDS)


def compress_context(history: list[dict], max_turns: int = 10) -> tuple[list[dict], MedicalContextSummary | None]:
    """
    上下文压缩

    Args:
        history: 完整对话历史
        max_turns: 超过此轮数触发压缩

    Returns:
        (压缩后的历史, 摘要对象)
    """
    if len(history) <= max_turns:
        return history, None

    # TODO: Week 7 实现完整压缩逻辑
    # 1. 提取结构化摘要（用 LLM 提取症状/用药/否认项）
    # 2. 标记关键轮次
    # 3. 保留关键轮原文 + 摘要替代其他轮
    summary = MedicalContextSummary(summary_text="上下文压缩功能开发中...")
    return history[-max_turns:], summary
