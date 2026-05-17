"""
HealthMate AI Engine - 调度核心
四条路径：紧急处理 / 报告管线 / Agent 工具 / 快速&深度通道
"""
from app.intent.schemas import IntentResult


# 意图优先级（数字越小优先级越高）
INTENT_PRIORITY = {
    "emergency": 0,
    "symptom_consult": 1,
    "drug_consult": 2,
    "report_parse": 3,
    "task_command": 4,
    "health_qa": 5,
    "casual_chat": 6,
}


def resolve_intent(result: IntentResult) -> str:
    """
    混合意图处理：取医疗优先级更高的意图
    例如 "我头疼，能吃布洛芬吗" → symptom_consult + drug_consult → 取 symptom_consult
    """
    if result.secondary_intent and result.secondary_confidence > 0.4:
        return min(
            [result.primary_intent, result.secondary_intent],
            key=lambda x: INTENT_PRIORITY.get(x, 99),
        )
    return result.primary_intent


def route(intent: str, confidence: float, turn_count: int) -> str:
    """
    模型调度器：根据意图 + 置信度 + 对话轮数，选择执行路径

    Returns:
        "emergency_handler"  - 紧急处理（最高优先级）
        "report_pipeline"    - 独立报告管线
        "agent_executor"     - Agent 工具调用
        "model_fast"         - 快速通道（轻量模型）
        "model_med"          - 深度通道（医疗微调模型）
    """
    # 路径 1：紧急处理
    if intent == "emergency":
        return "emergency_handler"

    # 路径 2：报告解读（独立管线，不走快速/深度通道）
    if intent == "report_parse":
        return "report_pipeline"

    # 路径 3：Agent 工具调用
    if intent == "task_command":
        return "agent_executor"

    # 路径 4A：快速通道
    if intent in ["casual_chat", "health_qa"] and confidence > 0.85:
        return "model_fast"

    # 路径 4B：深度通道
    if intent in ["symptom_consult", "drug_consult"]:
        return "model_med"

    # 多轮追问自动升级
    if turn_count > 5:
        return "model_med"

    return "model_fast"
