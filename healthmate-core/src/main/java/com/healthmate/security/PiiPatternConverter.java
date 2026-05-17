package com.healthmate.security;

import ch.qos.logback.classic.pattern.ClassicConverter;
import ch.qos.logback.classic.spi.ILoggingEvent;

/**
 * Logback 自定义 Pattern Converter
 * 在日志输出时自动对消息做 PII 脱敏
 *
 * logback.xml 中配置：
 *   <conversionRule conversionWord="piiMsg"
 *     converterClass="com.healthmate.security.PiiPatternConverter"/>
 *   <pattern>%d{HH:mm:ss} %-5level %logger{36} - %piiMsg%n</pattern>
 */
public class PiiPatternConverter extends ClassicConverter {

    @Override
    public String convert(ILoggingEvent event) {
        return PiiMaskingFilter.mask(event.getFormattedMessage());
    }
}
