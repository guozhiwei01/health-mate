"""
PII 脱敏过滤器（Python 侧）

在日志中自动替换手机号、身份证、对话原文
医疗合规必需组件
"""
import re
import logging


class PiiFilter(logging.Filter):
    """Loguru / logging 脱敏过滤器"""

    PATTERNS = [
        (re.compile(r'(1[3-9]\d)\d{4}(\d{4})'), r'\1****\2'),          # 手机号
        (re.compile(r'(\d{6})\d{8}(\d{4})'), r'\1********\2'),          # 身份证
        (re.compile(r'(content["\':=]+)[^,;"\']{20,}'), r'\1[已脱敏]'),  # 对话内容
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        return True


def mask_pii(text: str) -> str:
    """工具函数：对任意字符串做 PII 脱敏"""
    for pattern, replacement in PiiFilter.PATTERNS:
        text = pattern.sub(replacement, text)
    return text
