"""
模型调度器 - 四条路径路由
根据意图分类结果 + 置信度 + 对话轮数，决定走哪条路径

路径说明：
1. model_fast       - 快速通道（闲聊/健康问答）
2. model_med        - 深度通道（症状咨询/用药咨询）
3. report_pipeline  - 报告解读管线
4. agent_executor   - Agent 工具调用
5. emergency_handler - 紧急情况处理
"""
from app.intent.schemas import IntentResult, IntentType, INTENT_ROUTE_MAP

# 低置信度阈值：低于此值升级到深度通道
LOW_CONFIDENCE_THRESHOLD = 0.7

# 多轮升级阈值：超过此轮数，快速通道升级为深度通道
ESCALATION_TURN_COUNT = 3


def route(intent_result: IntentResult, turn_count: int = 0) -> str:
    """
    根据意图分类结果决定路由路径

    Args:
        intent_result: 意图分类结果
        turn_count: 当前对话轮数

    Returns:
        路由路径标识 (model_fast / model_med / report_pipeline / agent_executor / emergency_handler)
    """
    intent = intent_result.primary_intent
    confidence = intent_result.primary_confidence

    # 紧急情况始终最高优先级
    if intent == IntentType.EMERGENCY:
        return "emergency_handler"

    # 报告解读走独立管线
    if intent == IntentType.REPORT_PARSE:
        return "report_pipeline"

    # 任务指令走 Agent
    if intent == IntentType.TASK_COMMAND:
        return "agent_executor"

    # 低置信度升级：快速通道 → 深度通道
    base_route = INTENT_ROUTE_MAP.get(intent, "model_fast")
    if base_route == "model_fast" and confidence < LOW_CONFIDENCE_THRESHOLD:
        return "model_med"

    # 多轮升级：超过 N 轮的快速通道对话升级到深度通道
    if base_route == "model_fast" and turn_count >= ESCALATION_TURN_COUNT:
        return "model_med"

    return base_route


def resolve_intent(intent_result: IntentResult) -> str:
    """提取主意图字符串"""
    return intent_result.primary_intent.value
