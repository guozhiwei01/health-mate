"""Agent 工具 - 药品查询"""
from langchain_core.tools import tool


@tool
def search_drug(drug_name: str) -> str:
    """查询药品信息，包括适应症、禁忌、副作用、用法用量。参数：drug_name 药品名称"""
    # TODO: Week 9 实现，查询药品数据库
    return f"药品 {drug_name} 的详细信息查询中..."


@tool
def check_drug_interaction(drug_a: str, drug_b: str) -> str:
    """检查两种药品是否存在相互作用。参数：drug_a 药品A名称，drug_b 药品B名称"""
    # TODO: Week 9 实现
    return f"正在检查 {drug_a} 和 {drug_b} 的相互作用..."
