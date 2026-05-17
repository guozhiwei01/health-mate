package com.healthmate.config;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.Gauge;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import lombok.Getter;
import org.springframework.stereotype.Component;

import java.util.concurrent.atomic.AtomicInteger;

/**
 * HealthMate 业务黄金指标
 *
 * 面试要点（对标 Prometheus 四大黄金信号）：
 * - 流量：chat_total（按意图分）
 * - 延迟：chat_latency_seconds（P99/P95/P50）
 * - 错误：safety_trigger_total（安全兜底触发次数）
 * - 饱和度：active_chats（当前并发对话数）
 */
@Getter
@Component
public class BusinessMetrics {

    // 对话总量（按意图分类计数）
    private final Counter chatTotal;
    private final Counter chatSymptom;
    private final Counter chatDrug;
    private final Counter chatCasual;

    // 安全兜底触发（越多说明模型需要迭代）
    private final Counter safetyTriggerTotal;

    // 对话延迟分布
    private final Timer chatLatency;

    // RAG 检索命中率
    private final Counter ragHitTotal;
    private final Counter ragMissTotal;

    // 当前并发对话数
    private final AtomicInteger activeChats = new AtomicInteger(0);

    // 紧急事件计数
    private final Counter emergencyTotal;

    public BusinessMetrics(MeterRegistry registry) {
        this.chatTotal = Counter.builder("healthmate_chat_total")
                .description("Total chat requests")
                .register(registry);

        this.chatSymptom = Counter.builder("healthmate_chat_intent")
                .tag("intent", "symptom_consult")
                .description("Symptom consult chats")
                .register(registry);

        this.chatDrug = Counter.builder("healthmate_chat_intent")
                .tag("intent", "drug_consult")
                .description("Drug consult chats")
                .register(registry);

        this.chatCasual = Counter.builder("healthmate_chat_intent")
                .tag("intent", "casual_chat")
                .description("Casual chats")
                .register(registry);

        this.safetyTriggerTotal = Counter.builder("healthmate_safety_trigger_total")
                .description("Safety guardrail trigger count")
                .register(registry);

        this.chatLatency = Timer.builder("healthmate_chat_latency")
                .description("Chat response latency")
                .register(registry);

        this.ragHitTotal = Counter.builder("healthmate_rag_hit_total")
                .description("RAG retrieval hits")
                .register(registry);

        this.ragMissTotal = Counter.builder("healthmate_rag_miss_total")
                .description("RAG retrieval misses")
                .register(registry);

        this.emergencyTotal = Counter.builder("healthmate_emergency_total")
                .description("Emergency trigger count")
                .register(registry);

        Gauge.builder("healthmate_active_chats", activeChats, AtomicInteger::get)
                .description("Currently active chat sessions")
                .register(registry);
    }

    /** 按意图增加计数 */
    public void incrementChat(String intent) {
        chatTotal.increment();
        switch (intent) {
            case "symptom_consult" -> chatSymptom.increment();
            case "drug_consult" -> chatDrug.increment();
            case "casual_chat" -> chatCasual.increment();
        }
    }
}
