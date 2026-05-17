"""Agent 工具 - 提醒管理（调 Java Reminder Service）"""
from langchain_core.tools import tool


@tool
def create_reminder(user_id: int, content: str, scheduled_time: str) -> str:
    """创建健康提醒。参数：user_id 用户ID，content 提醒内容，scheduled_time 提醒时间（格式：2026-01-01 08:00）"""
    # TODO: Week 9 实现，HTTP 调用 Java Core
    return f"已为用户 {user_id} 创建提醒：{content}，时间：{scheduled_time}"


@tool
def list_reminders(user_id: int) -> str:
    """查询用户的健康提醒列表。参数：user_id 用户ID"""
    # TODO: Week 9 实现
    return f"用户 {user_id} 暂无提醒"
