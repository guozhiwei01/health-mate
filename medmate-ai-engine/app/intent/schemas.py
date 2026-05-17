"""
意图分类模块 - 数据结构定义
"""
from pydantic import BaseModel


# 7 类意图标签
INTENT_LABELS = {
    "casual_chat":     "日常闲聊",
    "health_qa":       "健康知识问答",
    "symptom_consult": "症状自述/咨询",
    "drug_consult":    "用药咨询",
    "report_parse":    "报告解读",
    "emergency":       "紧急情况",
    "task_command":    "任务型指令",
}


class IntentResult(BaseModel):
    """意图分类结果（Top-2 输出）"""
    primary_intent: str
    primary_confidence: float
    secondary_intent: str | None = None
    secondary_confidence: float = 0.0
