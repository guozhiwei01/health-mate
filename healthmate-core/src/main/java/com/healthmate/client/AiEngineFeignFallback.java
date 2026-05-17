package com.healthmate.client;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * Feign 降级兜底
 * AI Engine 不可用时，返回安全的默认回答
 */
@Slf4j
@Component
public class AiEngineFeignFallback implements AiEngineFeignClient {

    @Override
    public Map<String, Object> chat(String userInput, String sessionId, int turnCount) {
        log.warn("[FEIGN-FALLBACK] AI Engine unavailable, returning safe response");
        return Map.of(
                "response", "抱歉，AI 服务暂时不可用，请稍后重试。如有紧急情况请拨打 120。",
                "intent", "fallback",
                "model", "fallback",
                "provider", "local"
        );
    }

    @Override
    public String analyzeReport(String taskId, String imageUrl) {
        log.warn("[FEIGN-FALLBACK] Report analyze fallback: taskId={}", taskId);
        return "{\"status\":\"error\",\"message\":\"AI服务暂不可用\"}";
    }

    @Override
    public String healthCheck() {
        return "DOWN";
    }
}
