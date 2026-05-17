"""
跨语言链路追踪
Java Gateway 生成 X-Trace-Id，Python 侧通过 contextvars 接收
"""
from contextvars import ContextVar
from fastapi import Request

# 当前请求的 trace_id
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def get_trace_id() -> str:
    """获取当前请求的 trace_id"""
    return trace_id_var.get()


async def extract_trace_id(request: Request) -> str:
    """从请求头提取 trace_id"""
    trace_id = request.headers.get("X-Trace-Id", "")
    if trace_id:
        trace_id_var.set(trace_id)
    return trace_id
