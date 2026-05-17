"""
报告解读管线 - 三阶段独立管线
阶段 1：视觉提取（快速模型识别异常项）
阶段 2：RAG 检索（相关医学知识）
阶段 3：专业解读（医疗模型生成解读）
"""
import httpx

from app.config import settings


async def report_pipeline(image_url: str, task_id: str) -> str:
    """
    报告解读三阶段管线

    Args:
        image_url: 报告图片 URL（MinIO）
        task_id: 任务 ID

    Returns:
        解读结果文本
    """
    # === 阶段 1：视觉提取 ===
    # TODO: Week 5 实现
    # 用快速模型（多模态）提取结构化异常发现
    visual_findings = await _extract_findings(image_url)

    # === 阶段 2：RAG 检索 ===
    # TODO: Week 7 实现
    # 用异常项目检索医学知识库
    rag_context = await _retrieve_context(visual_findings)

    # === 阶段 3：专业解读 ===
    # TODO: Week 5 实现
    # 医疗模型基于视觉发现 + RAG 上下文生成解读
    report = await _generate_interpretation(visual_findings, rag_context)

    # 完成后回调 Java Core
    await _callback_java(task_id, report)

    return report


async def _extract_findings(image_url: str) -> dict:
    """阶段 1：视觉提取异常项"""
    # TODO: 接入快速模型多模态能力
    return {
        "abnormal_items": [],
        "normal_items": [],
        "raw_text": "",
    }


async def _retrieve_context(findings: dict) -> str:
    """阶段 2：RAG 检索相关医学知识"""
    # TODO: 接入 rag.retriever
    return ""


async def _generate_interpretation(findings: dict, context: str) -> str:
    """阶段 3：生成专业解读"""
    # TODO: 接入 healthmate_med 模型
    return "报告解读功能开发中..."


async def _callback_java(task_id: str, result: str):
    """完成后回调 Java Core"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{settings.java_core_url}/internal/report-task/{task_id}/complete",
                json={"result": result},
                timeout=10.0,
            )
    except Exception as e:
        print(f"⚠️ 回调 Java 失败: {e}")
