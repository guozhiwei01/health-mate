package com.healthmate.mq;

import com.healthmate.client.AiEngineClient;
import com.healthmate.service.ReportService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.springframework.stereotype.Component;

/**
 * 报告解读 MQ Consumer
 *
 * 流程（面试重点）：
 *   用户上传 → Java 存 DB + 投 MQ
 *   → 本 Consumer 消费 → 标记"处理中"
 *   → HTTP POST /internal/report/analyze 转发给 Python AI Engine
 *   → Python 处理完后回调 /internal/report-task/{id}/complete
 *
 * 为什么不让 Python 直接消费 MQ？
 *   → Python RocketMQ SDK 稳定性差，且跨语言 MQ 协议维护成本高
 *   → Java Consumer + HTTP 转发是生产环境最稳的方案
 */
@Slf4j
@Component
@RequiredArgsConstructor
@RocketMQMessageListener(
        topic = "report-analyze-topic",
        consumerGroup = "report-consumer"
)
public class ReportConsumer implements RocketMQListener<String> {

    private final ReportService reportService;
    private final AiEngineClient aiEngineClient;

    @Override
    public void onMessage(String taskId) {
        log.info("[MQ-CONSUMER] Received report task: {}", taskId);

        try {
            // 1. 标记处理中
            reportService.markProcessing(taskId);

            // 2. 获取任务详情
            var task = reportService.getTask(taskId);
            if (task == null) {
                log.error("[MQ-CONSUMER] Task not found: {}", taskId);
                return;
            }

            // 3. HTTP 转发给 Python AI Engine
            aiEngineClient.analyzeReport(taskId, task.getImageUrl());
            log.info("[MQ-CONSUMER] Forwarded to AI Engine: taskId={}", taskId);

        } catch (Exception e) {
            log.error("[MQ-CONSUMER] Processing failed: taskId={}, error={}",
                    taskId, e.getMessage());
            reportService.failTask(taskId, e.getMessage());
        }
    }
}
