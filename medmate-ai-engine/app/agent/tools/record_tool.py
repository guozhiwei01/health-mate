"""Agent 工具 - 健康数据记录"""
from langchain_core.tools import tool


@tool
def record_health_data(user_id: int, data_type: str, value: str) -> str:
    """记录用户健康数据。参数：user_id 用户ID，data_type 数据类型（血压/血糖/体重/心率），value 数值"""
    # TODO: Week 9 实现，HTTP 调用 Java Core
    return f"已记录用户 {user_id} 的 {data_type}：{value}"


@tool
def get_health_history(user_id: int, data_type: str, days: int = 7) -> str:
    """查询用户近期健康数据。参数：user_id 用户ID，data_type 数据类型，days 查询天数"""
    # TODO: Week 9 实现
    return f"用户 {user_id} 近 {days} 天 {data_type} 数据查询中..."
