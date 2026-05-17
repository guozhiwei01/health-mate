"""
LangGraph 状态图 - 核心编排引擎
严格对应 ARCHITECTURE.md 3.2 节
流程：意图分类 -> 路由 -> 推理 -> 安全检查 -> 输出
"""
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage

from app.intent.classifier import intent_classifier
from app.intent.schemas import IntentResult
from app.dispatcher import route, resolve_intent
from app.models.qwen_fast import qwen_fast
from app.models.healthmate_med import healthmate_med
from app.security.content_guard import content_guard


class HealthState(TypedDict):
    """对话状态"""
    user_input: str
    intent: str
    confidence: float
    turn_count: int
    selected_model: str
    rag_context: list
    response: str
    safety_flag: bool
    error: str | None


# ==================== Nodes ====================

def classify_intent_node(state: HealthState) -> dict:
    """Node: intent classification (0.5B LoRA)"""
    result = intent_classifier.classify(state["user_input"])
    route_path = route(result, state.get("turn_count", 0))
    return {
        "intent": result.primary_intent.value,
        "confidence": result.primary_confidence,
        "selected_model": route_path,
    }


def retrieve_context_node(state: HealthState) -> dict:
    """Node: RAG retrieval (pre-step for deep inference)"""
    # TODO: Week 7 - plug in rag.retriever + reranker
    return {"rag_context": []}


def fast_inference_node(state: HealthState) -> dict:
    """Node: fast channel inference (LangChain ChatOpenAI)"""
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
    """Node: deep channel inference (LangChain ChatOpenAI + RAG context)"""
    try:
        llm = healthmate_med.get_llm()
        system_prompt = healthmate_med.get_system_prompt()

        if state.get("rag_context"):
            context_text = "\n".join(state["rag_context"])
            system_prompt += f"\n\n[Reference]\n{context_text}"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["user_input"]),
        ]
        result = llm.invoke(messages)
        return {"response": result.content}
    except Exception as e:
        return {"response": "", "error": str(e)}


def report_pipeline_node(state: HealthState) -> dict:
    """Node: report analysis pipeline"""
    # TODO: Week 5 - plug in pipelines.report_pipeline
    return {"response": "Report analysis is under development. Please try again later."}


def agent_execute_node(state: HealthState) -> dict:
    """Node: agent tool execution"""
    # TODO: Week 7 - plug in LangChain Agent + Tools
    return {"response": "Task execution is under development. Please try again later."}


def emergency_handle_node(state: HealthState) -> dict:
    """Node: emergency handling"""
    return {
        "response": (
            "!! Emergency detected. Please call 120 immediately or go to the nearest ER.\n"
            "National psychological helpline: 400-161-9995\n"
            "Your safety is the top priority."
        )
    }


def safety_check_node(state: HealthState) -> dict:
    """Node: output safety check"""
    result = content_guard.check_output(state.get("response", ""))
    return {"safety_flag": result["is_blocked"]}


def fallback_node(state: HealthState) -> dict:
    """Node: fallback response (inference failure)"""
    return {"response": "Sorry, the service is busy. Please consult a doctor directly."}


def blocked_node(state: HealthState) -> dict:
    """Node: blocked response (unsafe output)"""
    return {"response": "Sorry, this content cannot be replied. Please consult a professional doctor."}


# ==================== Routing ====================

def route_to_model(state: HealthState) -> str:
    """Conditional edge: dispatch to the correct node"""
    return {
        "model_fast":        "fast_inference",
        "model_med":         "retrieve_context",
        "report_pipeline":   "report_pipeline",
        "agent_executor":    "agent_execute",
        "emergency_handler": "emergency_handle",
    }.get(state["selected_model"], "fast_inference")


def check_inference_result(state: HealthState) -> str:
    """Conditional edge: success -> safety check, failure -> fallback"""
    if state.get("response"):
        return "safety_check"
    return "fallback_response"


def check_safety(state: HealthState) -> str:
    """Conditional edge: safe -> END, blocked -> blocked_response"""
    if not state.get("safety_flag"):
        return END
    return "blocked_response"


# ==================== Build graph ====================

def build_health_graph():
    """Build and compile the LangGraph state graph"""
    workflow = StateGraph(HealthState)

    # Register nodes
    workflow.add_node("classify_intent",   classify_intent_node)
    workflow.add_node("retrieve_context",  retrieve_context_node)
    workflow.add_node("fast_inference",    fast_inference_node)
    workflow.add_node("deep_inference",    deep_inference_node)
    workflow.add_node("report_pipeline",   report_pipeline_node)
    workflow.add_node("agent_execute",     agent_execute_node)
    workflow.add_node("emergency_handle",  emergency_handle_node)
    workflow.add_node("safety_check",      safety_check_node)
    workflow.add_node("fallback_response", fallback_node)
    workflow.add_node("blocked_response",  blocked_node)

    # Entry
    workflow.set_entry_point("classify_intent")

    # classify_intent -> route to one of 5 paths
    workflow.add_conditional_edges(
        "classify_intent",
        route_to_model,
        {
            "fast_inference":   "fast_inference",
            "retrieve_context": "retrieve_context",
            "report_pipeline":  "report_pipeline",
            "agent_execute":    "agent_execute",
            "emergency_handle": "emergency_handle",
        }
    )

    # Deep channel: RAG -> inference
    workflow.add_edge("retrieve_context", "deep_inference")

    # Inference result check
    workflow.add_conditional_edges("deep_inference", check_inference_result,
        {"safety_check": "safety_check", "fallback_response": "fallback_response"})
    workflow.add_conditional_edges("fast_inference", check_inference_result,
        {"safety_check": "safety_check", "fallback_response": "fallback_response"})

    # Safety check
    workflow.add_conditional_edges("safety_check", check_safety,
        {END: END, "blocked_response": "blocked_response"})

    # Other paths
    workflow.add_edge("report_pipeline",   "safety_check")
    workflow.add_edge("agent_execute",     "safety_check")
    workflow.add_edge("emergency_handle",  END)
    workflow.add_edge("fallback_response", END)
    workflow.add_edge("blocked_response",  END)

    return workflow.compile()


# Compile (singleton)
health_app = build_health_graph()
