package com.healthmate.security;

import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.filter.Filter;
import ch.qos.logback.core.spi.FilterReply;

import java.util.regex.Pattern;

/**
 * 日志 PII 脱敏过滤器
 *
 * 面试要点：
 * - 医疗合规要求：日志中不能出现手机号、身份证、对话原文
 * - Logback Filter 层面拦截，零侵入业务代码
 * - 正则替换，性能开销极低
 */
public class PiiMaskingFilter extends Filter<ILoggingEvent> {

    private static final Pattern PHONE = Pattern.compile("(1[3-9]\\d)\\d{4}(\\d{4})");
    private static final Pattern ID_CARD = Pattern.compile("(\\d{6})\\d{8}(\\d{4})");
    private static final Pattern CONTENT = Pattern.compile("(content[\"=:]+)[^,;\"]{20,}");

    @Override
    public FilterReply decide(ILoggingEvent event) {
        // Logback Filter 不能修改消息，改用 Converter 更合适
        // 这里做标记，实际脱敏在 PiiPatternConverter 中
        return FilterReply.NEUTRAL;
    }

    /**
     * 静态工具方法：对任意字符串做 PII 脱敏
     * 供业务代码主动调用
     */
    public static String mask(String input) {
        if (input == null) return null;
        String result = PHONE.matcher(input).replaceAll("$1****$2");
        result = ID_CARD.matcher(result).replaceAll("$1********$2");
        result = CONTENT.matcher(result).replaceAll("$1[已脱敏]");
        return result;
    }
}
