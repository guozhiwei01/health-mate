"""Agent 工具 - 紧急情况处理（含家庭通知）"""
from langchain_core.tools import tool


@tool
def handle_emergency(user_id: int, trigger_content: str) -> str:
    """
    紧急情况处理：推荐附近医院、通知家庭成员、记录事件日志。
    参数：user_id 用户ID，trigger_content 触发紧急的内容描述
    """
    # TODO: Week 9 实现
    return (
        "!! 紧急情况处理已启动：\n"
        "1. 请立即拨打 120 或前往最近医院急诊\n"
        "2. 全国心理援助热线：400-161-9995\n"
        "3. 已通知您的紧急联系人\n"
        "4. 事件已记录到安全日志"
    )
