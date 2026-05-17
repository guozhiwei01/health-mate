"""
HealthMate AI Engine - FastAPI 入口
端口：8090

技术栈：FastAPI + LangChain + LangGraph + DashScope/Ollama
"""
from dotenv import load_dotenv
load_dotenv()  # 加载 .env 到 os.environ（LangSmith 需要）

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时加载模型，关闭时释放资源"""
    # 加载意图分类器
    from app.intent.classifier import intent_classifier
    intent_classifier.load()

    # 构建 LangGraph 状态图
    from app.agent.health_graph import health_app
    app.state.health_app = health_app

    print(f"[START] {settings.app_name} | provider={settings.ai_provider} | model={settings.active_fast_model}")
    yield
    print(f"[STOP] {settings.app_name} shutting down")


app = FastAPI(
    title=settings.app_name,
    description="自训医疗大模型驱动的 AI 健康助手引擎（LangChain + LangGraph）",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 健康检查 ====================

@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "service": settings.app_name,
        "ai_provider": settings.ai_provider,
        "model": settings.active_fast_model,
    }


# ==================== 核心接口 ====================

@app.post("/api/intent/classify", tags=["AI 核心"])
async def classify_intent(text: str):
    """
    意图分类（0.5B LoRA 模型）
    输出 Top-2 意图 + 置信度
    """
    from app.intent.classifier import intent_classifier
    result = intent_classifier.classify(text)
    return result.model_dump()


@app.post("/api/chat", tags=["AI 核心"])
async def chat(user_input: str, session_id: str = "", turn_count: int = 0):
    """
    对话接口 - 走 LangGraph 完整链路
    意图分类 → 模型路由 → 推理 → 安全检查 → 输出
    """
    # 构建初始状态
    initial_state = {
        "user_input": user_input,
        "intent": "",
        "confidence": 0.0,
        "turn_count": turn_count,
        "selected_model": "",
        "rag_context": [],
        "response": "",
        "safety_flag": False,
        "error": None,
    }

    # 运行 LangGraph 状态图
    result = app.state.health_app.invoke(initial_state)

    return {
        "response": result["response"],
        "intent": result["intent"],
        "model": result["selected_model"],
        "provider": settings.ai_provider,
    }


@app.post("/api/chat/quick", tags=["AI 核心"])
async def chat_quick(user_input: str, mode: str = "fast"):
    """
    快捷对话（跳过 LangGraph，直接调模型）
    mode: "fast" 快速通道, "med" 深度通道
    """
    from langchain_core.messages import SystemMessage, HumanMessage
    from app.models.qwen_fast import qwen_fast
    from app.models.healthmate_med import healthmate_med

    provider = healthmate_med if mode == "med" else qwen_fast
    llm = provider.get_llm()
    messages = [
        SystemMessage(content=provider.get_system_prompt()),
        HumanMessage(content=user_input),
    ]
    result = llm.invoke(messages)
    return {
        "response": result.content,
        "model": llm.model_name,
        "provider": settings.ai_provider,
    }


@app.post("/internal/report/analyze", tags=["内部接口"])
async def analyze_report(task_id: str, image_url: str):
    """
    报告异步解读（Java Core 内部调用）
    流程：Java Consumer -> HTTP POST 这里 -> 处理 -> 回调 Java
    """
    from app.pipelines.report_pipeline import report_pipeline
    # 异步执行，不阻塞
    import asyncio
    asyncio.create_task(report_pipeline(image_url, task_id))
    return {"status": "processing", "task_id": task_id}


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.app_port, reload=True)
