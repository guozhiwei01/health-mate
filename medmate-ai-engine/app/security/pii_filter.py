"""
日志 PII 脱敏过滤器
自动过滤手机号、身份证、对话内容
"""
import re
import logging


class PiiFilter(logging.Filter):
    """PII 脱敏过滤器"""

    PATTERNS = [
        (re.compile(r"\d{11}"), "***手机号***"),
        (re.compile(r"\d{17}[\dXx]"), "***身份证***"),
        (re.compile(r'content="[^"]{20,}"'), 'content="[脱敏]"'),
    ]

    def filter(self, record):
        msg = str(record.getMessage())
        for pattern, replacement in self.PATTERNS:
            msg = pattern.sub(replacement, msg)
        record.msg = msg
        return True


def setup_pii_logging():
    """配置带脱敏的日志"""
    logger = logging.getLogger("healthmate")
    logger.addFilter(PiiFilter())
    return logger
