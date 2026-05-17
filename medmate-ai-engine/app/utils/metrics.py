"""
Prometheus 业务指标
技术指标 + 业务黄金指标
"""
from prometheus_client import Counter, Histogram, Gauge


# ==================== 技术指标 ====================

inference_latency = Histogram(
    "healthmate_inference_seconds",
    "模型推理延迟（秒）",
    labelnames=["model", "intent"],
)

route_ratio = Gauge(
    "healthmate_route_ratio",
    "各路径路由比例",
    labelnames=["path"],
)

# ==================== 业务黄金指标 ====================

safety_trigger = Counter(
    "healthmate_safety_trigger_total",
    "安全兜底触发次数",
)

user_satisfaction = Gauge(
    "healthmate_user_satisfaction",
    "用户满意度（👍/👎 比率）",
)

escalation_rate = Gauge(
    "healthmate_escalation_rate",
    "快速通道升级到深度通道的比率",
)

rag_hit_rate = Gauge(
    "healthmate_rag_hit_rate",
    "RAG 检索命中率",
)

emergency_count = Counter(
    "healthmate_emergency_total",
    "紧急情况触发次数",
)
