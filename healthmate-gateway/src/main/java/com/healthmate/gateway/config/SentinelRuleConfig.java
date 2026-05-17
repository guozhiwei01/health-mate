package com.healthmate.gateway.config;

import com.alibaba.csp.sentinel.adapter.gateway.common.SentinelGatewayConstants;
import com.alibaba.csp.sentinel.adapter.gateway.common.api.ApiDefinition;
import com.alibaba.csp.sentinel.adapter.gateway.common.api.ApiPathPredicateItem;
import com.alibaba.csp.sentinel.adapter.gateway.common.api.ApiPredicateItem;
import com.alibaba.csp.sentinel.adapter.gateway.common.api.GatewayApiDefinitionManager;
import com.alibaba.csp.sentinel.adapter.gateway.common.rule.GatewayFlowRule;
import com.alibaba.csp.sentinel.adapter.gateway.common.rule.GatewayRuleManager;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.HashSet;
import java.util.Set;

/**
 * Sentinel 网关限流规则配置
 *
 * 面试要点：
 * - 与 Redis 限流的区别：Sentinel 是进程内限流，不依赖外部存储，更快
 * - Gateway 层限流 vs Service 层限流：Gateway 拦截更早，保护下游
 * - 支持按 API 分组、按路由 ID 限流
 * - 生产环境规则推送到 Nacos 动态更新，不需要重启
 */
@Slf4j
@Component
public class SentinelRuleConfig {

    @PostConstruct
    public void init() {
        initCustomizedApis();
        initGatewayRules();
        log.info("[SENTINEL] Gateway flow rules initialized");
    }

    /**
     * API 分组定义
     */
    private void initCustomizedApis() {
        Set<ApiDefinition> definitions = new HashSet<>();

        // 对话类 API 分组
        ApiDefinition chatApi = new ApiDefinition("chat-api")
                .setPredicateItems(new HashSet<ApiPredicateItem>() {{
                    add(new ApiPathPredicateItem()
                            .setPattern("/api/chat/**")
                            .setMatchStrategy(SentinelGatewayConstants.URL_MATCH_STRATEGY_PREFIX));
                }});

        // 报告类 API 分组
        ApiDefinition reportApi = new ApiDefinition("report-api")
                .setPredicateItems(new HashSet<ApiPredicateItem>() {{
                    add(new ApiPathPredicateItem()
                            .setPattern("/api/report/**")
                            .setMatchStrategy(SentinelGatewayConstants.URL_MATCH_STRATEGY_PREFIX));
                }});

        definitions.add(chatApi);
        definitions.add(reportApi);
        GatewayApiDefinitionManager.loadApiDefinitions(definitions);
    }

    /**
     * 限流规则
     */
    private void initGatewayRules() {
        Set<GatewayFlowRule> rules = new HashSet<>();

        // 对话接口：QPS 限制 50
        rules.add(new GatewayFlowRule("chat-api")
                .setResourceMode(SentinelGatewayConstants.RESOURCE_MODE_CUSTOM_API_NAME)
                .setCount(50)
                .setIntervalSec(1));

        // 报告接口：QPS 限制 20（更重的操作）
        rules.add(new GatewayFlowRule("report-api")
                .setResourceMode(SentinelGatewayConstants.RESOURCE_MODE_CUSTOM_API_NAME)
                .setCount(20)
                .setIntervalSec(1));

        // 全局路由级限流
        rules.add(new GatewayFlowRule("core-service")
                .setCount(100)
                .setIntervalSec(1));

        GatewayRuleManager.loadRules(rules);
    }
}
