"""
意图分类模块 - 数据结构定义
"""
from enum import Enum
from pydantic import BaseModel


class IntentType(str, Enum):
    """7 类意图标签"""
    CASUAL_CHAT = "casual_chat"
    HEALTH_QA = "health_qa"
    SYMPTOM_CONSULT = "symptom_consult"
    DRUG_CONSULT = "drug_consult"
    REPORT_PARSE = "report_parse"
    EMERGENCY = "emergency"
    TASK_COMMAND = "task_command"


# 意图 → 中文名映射
INTENT_LABELS = {
    IntentType.CASUAL_CHAT:     "日常闲聊",
    IntentType.HEALTH_QA:       "健康知识问答",
    IntentType.SYMPTOM_CONSULT: "症状自述/咨询",
    IntentType.DRUG_CONSULT:    "用药咨询",
    IntentType.REPORT_PARSE:    "报告解读",
    IntentType.EMERGENCY:       "紧急情况",
    IntentType.TASK_COMMAND:    "任务型指令",
}

# 意图 → 路由路径映射
INTENT_ROUTE_MAP = {
    IntentType.CASUAL_CHAT:     "model_fast",
    IntentType.HEALTH_QA:       "model_fast",
    IntentType.SYMPTOM_CONSULT: "model_med",
    IntentType.DRUG_CONSULT:    "model_med",
    IntentType.REPORT_PARSE:    "report_pipeline",
    IntentType.EMERGENCY:       "emergency_handler",
    IntentType.TASK_COMMAND:    "agent_executor",
}


class IntentResult(BaseModel):
    """意图分类结果（Top-2 输出）"""
    primary_intent: IntentType = IntentType.HEALTH_QA
    primary_confidence: float = 0.0
    secondary_intent: IntentType | None = None
    secondary_confidence: float = 0.0
    latency_ms: float = 0.0
