"""
LangGraph 状态图 - 核心编排引擎
严格对应 ARCHITECTURE.md 3.2 节
流程：意图分类 → 路由 → 推理 → 安全检查 → 输出
"""
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.dispatcher import route, resolve_intent
from app.intent.classifier import intent_classifier
from app.models.qwen_fast import qwen_fast
from app.models.healthmate_med import healthmate_med
from app.security.content_guard import content_guard


class HealthState(TypedDict):
    """对话状态（对应 ARCHITECTURE.md 3.2）"""
    user_input: str
    intent: str
    confidence: float
    turn_count: int
    selected_model: str
    rag_context: list
    response: str
    safety_flag: bool
    error: str | None


# ==================== 节点定义 ====================

def classify_intent_node(state: HealthState) -> dict:
    """节点：意图分类（0.5B LoRA 模型）"""
    result = intent_classifier.classify(state["user_input"])
    resolved = resolve_intent(result)
    return {
        "intent": resolved,
        "confidence": result.primary_confidence,
    }


def route_model_node(state: HealthState) -> dict:
    """节点：模型路由（四条路径）"""
    selected = route(state["intent"], state["confidence"], state["turn_count"])
    return {"selected_model": selected}


def retrieve_context_node(state: HealthState) -> dict:
    """节点：RAG 检索（深度通道前置）"""
    # TODO: Week 7 接入 rag.retriever + reranker
    return {"rag_context": []}


def fast_inference_node(state: HealthState) -> dict:
    """节点：快速通道推理（LangChain ChatOpenAI）"""
    try:
        llm = qwen_fast.get_llm()
        messages = [
            SystemMessage(content=qwen_fast.get_system_prompt()),
            HumanMessage(content=state["user_input"]),
        ]
        result = llm.invoke(messages)
        return {"response": result.content}
    except Exception as e:
        return {"response": "", "error": str(e)}


def deep_inference_node(state: HealthState) -> dict:
    """节点：深度通道推理（LangChain ChatOpenAI + RAG 上下文）"""
    try:
        llm = healthmate_med.get_llm()
        system_prompt = healthmate_med.get_system_prompt()

        # 注入 RAG 上下文
        if state.get("rag_context"):
            context_text = "\n".join(state["rag_context"])
            system_prompt += f"\n\n【参考资料】\n{context_text}"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["user_input"]),
        ]
        result = llm.invoke(messages)
        return {"response": result.content}
    except Exception as e:
        return {"response": "", "error": str(e)}


def report_pipeline_node(state: HealthState) -> dict:
    """节点：报告解读管线（三阶段独立管线）"""
    # TODO: Week 5 接入 pipelines.report_pipeline
    return {"response": "报告解读功能开发中，请稍后再试。"}


def agent_execute_node(state: HealthState) -> dict:
    """节点：Agent 工具调用"""
    # TODO: Week 7 接入 LangChain Agent + Tools
    return {"response": "任务执行功能开发中，请稍后再试。"}


def emergency_handle_node(state: HealthState) -> dict:
    """节点：紧急处理"""
    return {
        "response": (
            "!! 检测到紧急情况，请立即拨打 120 或前往最近医院急诊。\n"
            "全国心理援助热线：400-161-9995\n"
            "请不要犹豫，您的生命安全最重要。"
        )
    }


def safety_check_node(state: HealthState) -> dict:
    """节点：安全检查"""
    result = content_guard.check_output(state.get("response", ""))
    return {"safety_flag": result["is_blocked"]}


def fallback_node(state: HealthState) -> dict:
    """节点：降级回复（推理失败时兜底）"""
    return {"response": "抱歉，当前服务繁忙，建议您直接咨询医生。以上建议仅供参考。"}


def blocked_node(state: HealthState) -> dict:
    """节点：安全拦截（输出不安全时替换）"""
    return {"response": "抱歉，该内容无法回复。如有健康问题请咨询专业医生。"}


# ==================== 路由函数 ====================

def route_to_model(state: HealthState) -> str:
    """条件路由：根据 selected_model 分发到对应节点"""
    return {
        "model_fast":         "fast_inference",
        "model_med":          "retrieve_context",
        "report_pipeline":    "report_pipeline",
        "agent_executor":     "agent_execute",
        "emergency_handler":  "emergency_handle",
    }.get(state["selected_model"], "fast_inference")


def check_inference_result(state: HealthState) -> str:
    """条件路由：推理成功走安全检查，失败走降级"""
    if state.get("response"):
        return "safety_check"
    return "fallback_response"


def check_safety(state: HealthState) -> str:
    """条件路由：安全通过直接输出，不安全走拦截"""
    if not state.get("safety_flag"):
        return END
    return "blocked_response"


# ==================== 构建状态图 ====================

def build_health_graph() -> StateGraph:
    """
    构建 LangGraph 状态图
    严格对应 ARCHITECTURE.md 3.2 节
    """
    workflow = StateGraph(HealthState)

    # 注册所有节点
    workflow.add_node("classify_intent",   classify_intent_node)
    workflow.add_node("route_model",       route_model_node)
    workflow.add_node("retrieve_context",  retrieve_context_node)
    workflow.add_node("fast_inference",    fast_inference_node)
    workflow.add_node("deep_inference",    deep_inference_node)
    workflow.add_node("report_pipeline",   report_pipeline_node)
    workflow.add_node("agent_execute",     agent_execute_node)
    workflow.add_node("emergency_handle",  emergency_handle_node)
    workflow.add_node("safety_check",      safety_check_node)
    workflow.add_node("fallback_response", fallback_node)
    workflow.add_node("blocked_response",  blocked_node)

    # 入口
    workflow.set_entry_point("classify_intent")
    workflow.add_edge("classify_intent", "route_model")

    # 路由到四条路径
    workflow.add_conditional_edges(
        "route_model",
        route_to_model,
        {
            "fast_inference":    "fast_inference",
            "retrieve_context":  "retrieve_context",
            "report_pipeline":   "report_pipeline",
            "agent_execute":     "agent_execute",
            "emergency_handle":  "emergency_handle",
        }
    )

    # 深度通道：先 RAG 再推理
    workflow.add_edge("retrieve_context", "deep_inference")

    # 推理结果检查（成功 → 安全检查，失败 → 降级）
    workflow.add_conditional_edges("deep_inference", check_inference_result,
        {"safety_check": "safety_check", "fallback_response": "fallback_response"})
    workflow.add_conditional_edges("fast_inference", check_inference_result,
        {"safety_check": "safety_check", "fallback_response": "fallback_response"})

    # 安全检查（通过 → END，拦截 → blocked）
    workflow.add_conditional_edges("safety_check", check_safety,
        {END: END, "blocked_response": "blocked_response"})

    # 其他路径直接到安全检查或 END
    workflow.add_edge("report_pipeline",   "safety_check")
    workflow.add_edge("agent_execute",     "safety_check")
    workflow.add_edge("emergency_handle",  END)
    workflow.add_edge("fallback_response", END)
    workflow.add_edge("blocked_response",  END)

    return workflow.compile()


# 编译状态图（全局单例）
health_app = build_health_graph()
