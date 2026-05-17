"""
HealthMate AI Engine - FastAPI Entry
Port: 8090

Tech: FastAPI + LangChain + LangGraph + DashScope/Ollama + LangSmith
"""
from dotenv import load_dotenv
load_dotenv()  # Load .env to os.environ (LangSmith needs this)

import asyncio
import json
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from langchain_core.messages import SystemMessage, HumanMessage

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifecycle: load models on startup, release on shutdown"""
    # Load intent classifier (0.5B LoRA)
    from app.intent.classifier import intent_classifier
    intent_classifier.load()

    # Build LangGraph state graph
    from app.agent.health_graph import health_app
    app.state.health_app = health_app

    print(f"[START] {settings.app_name} | provider={settings.ai_provider} | model={settings.active_fast_model}")
    yield
    print(f"[STOP] {settings.app_name} shutting down")


app = FastAPI(
    title=settings.app_name,
    description="AI Health Assistant Engine (LangChain + LangGraph)",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Health Check ====================

@app.get("/health", tags=["System"])
async def health_check():
    """Health check"""
    return {
        "status": "ok",
        "service": settings.app_name,
        "ai_provider": settings.ai_provider,
        "model": settings.active_fast_model,
    }


# ==================== Core API ====================

@app.post("/api/intent/classify", tags=["AI Core"])
async def classify_intent(text: str):
    """
    Intent classification (0.5B LoRA model)
    Output: Top-2 intent + confidence
    """
    from app.intent.classifier import intent_classifier
    result = intent_classifier.classify(text)
    return result.model_dump()


@app.post("/api/chat", tags=["AI Core"])
async def chat(user_input: str, session_id: str = "", turn_count: int = 0):
    """
    Chat API - Full LangGraph pipeline
    Intent classify -> Route -> Inference -> Safety check -> Output
    """
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

    result = app.state.health_app.invoke(initial_state)

    return {
        "response": result["response"],
        "intent": result["intent"],
        "model": result["selected_model"],
        "provider": settings.ai_provider,
    }


@app.post("/api/chat/stream", tags=["AI Core"])
async def chat_stream(user_input: str, session_id: str = "", turn_count: int = 0):
    """
    Streaming Chat API - SSE (Server-Sent Events)
    Same pipeline as /api/chat, but streams the LLM response token by token
    """
    from app.intent.classifier import intent_classifier
    from app.dispatcher import route
    from app.models.qwen_fast import qwen_fast
    from app.models.healthmate_med import healthmate_med
    from app.security.content_guard import content_guard

    # Step 1: Intent classification
    intent_result = intent_classifier.classify(user_input)
    route_path = route(intent_result, turn_count)
    intent_str = intent_result.primary_intent.value

    async def event_stream():
        # Send metadata first
        meta = {
            "type": "meta",
            "intent": intent_str,
            "model": route_path,
            "provider": settings.ai_provider,
        }
        yield f"data: {json.dumps(meta, ensure_ascii=False)}\n\n"

        # Step 2: Handle non-streaming paths
        if route_path == "emergency_handler":
            msg = (
                "!! EMERGENCY DETECTED !!\n"
                "Please call 120 immediately or go to the nearest ER.\n"
                "National psychological helpline: 400-161-9995\n"
                "Your safety is the top priority."
            )
            yield f"data: {json.dumps({'type': 'token', 'content': msg}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        if route_path == "report_pipeline":
            yield f"data: {json.dumps({'type': 'token', 'content': 'Report analysis pipeline is under development.'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        if route_path == "agent_executor":
            yield f"data: {json.dumps({'type': 'token', 'content': 'Agent tool execution is under development.'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            return

        # Step 3: Streaming LLM inference
        if route_path == "model_med":
            provider = healthmate_med
        else:
            provider = qwen_fast

        llm = provider.get_llm()
        messages = [
            SystemMessage(content=provider.get_system_prompt()),
            HumanMessage(content=user_input),
        ]

        full_response = ""
        try:
            for chunk in llm.stream(messages):
                token = chunk.content
                if token:
                    full_response += token
                    yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

        # Step 4: Safety check on full response
        safety = content_guard.check_output(full_response)
        if safety["is_blocked"]:
            yield f"data: {json.dumps({'type': 'blocked', 'content': 'This content has been blocked by safety filter.'}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/chat/quick", tags=["AI Core"])
async def chat_quick(user_input: str, mode: str = "fast"):
    """
    Quick chat (bypass LangGraph, direct model call)
    mode: "fast" or "med"
    """
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


@app.post("/internal/report/analyze", tags=["Internal"])
async def analyze_report(task_id: str, image_url: str):
    """
    Report async analysis (called by Java Core internally)
    Flow: Java Consumer -> HTTP POST here -> process -> callback Java
    """
    from app.pipelines.report_pipeline import report_pipeline
    asyncio.create_task(report_pipeline(image_url, task_id))
    return {"status": "processing", "task_id": task_id}


# ==================== Static Frontend ====================

# Mount static files (frontend demo)
import os
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


# ==================== Entry ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.app_port, reload=True)
