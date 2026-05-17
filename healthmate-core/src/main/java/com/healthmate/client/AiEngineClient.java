package com.healthmate.client;

import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;

import jakarta.annotation.PostConstruct;

/**
 * AI Engine HTTP 客户端
 * Java Core → Python AI Engine (port 8090)
 * 支持同步调用和 SSE 流式转发
 */
@Slf4j
@Component
public class AiEngineClient {

    @Value("${ai-engine.base-url}")
    private String baseUrl;

    private WebClient webClient;

    @PostConstruct
    public void init() {
        this.webClient = WebClient.builder()
                .baseUrl(baseUrl)
                .build();
        log.info("[AI-CLIENT] Initialized, baseUrl={}", baseUrl);
    }

    /**
     * 同步调用 /api/chat
     */
    public ChatResponse chat(String userInput, String sessionId, int turnCount) {
        return webClient.post()
                .uri(uriBuilder -> uriBuilder.path("/api/chat")
                        .queryParam("user_input", userInput)
                        .queryParam("session_id", sessionId)
                        .queryParam("turn_count", turnCount)
                        .build())
                .retrieve()
                .bodyToMono(ChatResponse.class)
                .block();
    }

    /**
     * SSE 流式调用 /api/chat/stream
     * 返回 Flux<String>，每个元素是一个 SSE data 行
     */
    public Flux<String> chatStream(String userInput, String sessionId, int turnCount) {
        return webClient.post()
                .uri(uriBuilder -> uriBuilder.path("/api/chat/stream")
                        .queryParam("user_input", userInput)
                        .queryParam("session_id", sessionId)
                        .queryParam("turn_count", turnCount)
                        .build())
                .accept(MediaType.TEXT_EVENT_STREAM)
                .retrieve()
                .bodyToFlux(String.class);
    }

    /**
     * 报告解读（异步 HTTP 转发给 Python）
     * MQ Consumer 调用此方法
     */
    public void analyzeReport(String taskId, String imageUrl) {
        webClient.post()
                .uri(uriBuilder -> uriBuilder.path("/internal/report/analyze")
                        .queryParam("task_id", taskId)
                        .queryParam("image_url", imageUrl)
                        .build())
                .retrieve()
                .bodyToMono(String.class)
                .block();
        log.info("[AI-CLIENT] Report analyze sent: taskId={}", taskId);
    }

    /**
     * 健康检查
     */
    public boolean healthCheck() {
        try {
            webClient.get()
                    .uri("/health")
                    .retrieve()
                    .bodyToMono(String.class)
                    .block();
            return true;
        } catch (Exception e) {
            log.warn("[AI-CLIENT] Health check failed: {}", e.getMessage());
            return false;
        }
    }

    @Data
    public static class ChatResponse {
        private String response;
        private String intent;
        private String model;
        private String provider;
    }
}
