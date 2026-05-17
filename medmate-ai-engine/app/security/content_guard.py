"""
输出安全检查
- 检测危险内容（自残/自杀倾向）
- 检测不当医疗建议
- 触发安全兜底
"""


class ContentGuard:
    """输出安全检查器"""

    # 紧急关键词
    EMERGENCY_KEYWORDS = ["自杀", "自残", "不想活", "跳楼", "割腕"]

    # 禁止直接给出的建议
    BLOCKED_PATTERNS = ["确诊为", "你得了", "必须吃"]

    def check_input(self, text: str) -> dict:
        """
        检查用户输入是否包含紧急内容

        Returns:
            {"is_emergency": bool, "reason": str}
        """
        for kw in self.EMERGENCY_KEYWORDS:
            if kw in text:
                return {"is_emergency": True, "reason": f"检测到紧急关键词: {kw}"}
        return {"is_emergency": False, "reason": ""}

    def check_output(self, text: str) -> dict:
        """
        检查模型输出是否安全

        Returns:
            {"is_blocked": bool, "reason": str}
        """
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in text:
                return {"is_blocked": True, "reason": f"输出包含不当表述: {pattern}"}
        return {"is_blocked": False, "reason": ""}


# 全局单例
content_guard = ContentGuard()
