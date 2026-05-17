package com.healthmate.client;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.Map;

/**
 * OpenFeign 声明式调用 Python AI Engine
 *
 * 面试要点：
 * - @FeignClient 声明式 HTTP，比手写 WebClient 更简洁
 * - url 直连（Python 非 Java 服务，不走 Nacos）
 * - 如果 Python 也注册 Nacos，可以用 name 替代 url 实现负载均衡
 * - fallback 降级：AI 不可用时返回兜底回答
 */
@FeignClient(
        name = "ai-engine",
        url = "${ai-engine.base-url}",
        fallback = AiEngineFeignFallback.class
)
public interface AiEngineFeignClient {

    @PostMapping("/api/chat")
    Map<String, Object> chat(
            @RequestParam("user_input") String userInput,
            @RequestParam("session_id") String sessionId,
            @RequestParam("turn_count") int turnCount
    );

    @PostMapping("/internal/report/analyze")
    String analyzeReport(
            @RequestParam("task_id") String taskId,
            @RequestParam("image_url") String imageUrl
    );

    @GetMapping("/health")
    String healthCheck();
}
