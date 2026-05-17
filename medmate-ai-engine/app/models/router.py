"""
模型灰度路由 - 按 user_id hash 稳定分流
支持模型版本 A/B 测试
"""
from app.config import settings


# 灰度配置（后续从 Redis 读取，可热更新）
DEFAULT_ROUTING_CONFIG = {
    "model_med": {
        "v1": {"weight": 1.0, "model_name": settings.ollama_med_model},
        # 新版本上线时：
        # "v2": {"weight": 0.1, "model_name": "healthmate-med-v2"},
    }
}


def select_model_version(model_name: str, user_id: int) -> str:
    """
    按 user_id hash 稳定分流，同一用户始终用同一版本

    Args:
        model_name: 模型标识（如 "model_med"）
        user_id: 用户 ID

    Returns:
        实际使用的模型名称
    """
    config = DEFAULT_ROUTING_CONFIG.get(model_name)
    if not config:
        return model_name

    bucket = hash(str(user_id)) % 100
    cumulative = 0
    for version, cfg in config.items():
        cumulative += cfg["weight"] * 100
        if bucket < cumulative:
            return cfg["model_name"]

    # fallback
    return list(config.values())[0]["model_name"]
