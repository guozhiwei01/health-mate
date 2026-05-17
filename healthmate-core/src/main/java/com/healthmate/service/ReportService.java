package com.healthmate.service;

import com.healthmate.client.AiEngineClient;
import com.healthmate.entity.ReportTask;
import com.healthmate.mapper.ReportTaskMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.core.RocketMQTemplate;
import org.springframework.stereotype.Service;

import java.util.UUID;

/**
 * 报告解读 Service
 * 流程：用户上传 → 创建任务 → 投 MQ → Consumer 消费 → HTTP 转发 Python AI
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ReportService {

    private final ReportTaskMapper reportTaskMapper;
    private final RocketMQTemplate rocketMQTemplate;

    public static final String TOPIC = "report-analyze-topic";

    /**
     * 提交报告解读任务（异步）
     * 1. 创建 DB 记录（状态=待处理）
     * 2. 投递 RocketMQ
     */
    public ReportTask submitReport(Long userId, String imageUrl) {
        ReportTask task = new ReportTask();
        task.setId(UUID.randomUUID().toString().replace("-", ""));
        task.setUserId(userId);
        task.setImageUrl(imageUrl);
        task.setStatus(0);  // 0=待处理
        reportTaskMapper.insert(task);

        // 投递 MQ
        rocketMQTemplate.convertAndSend(TOPIC, task.getId());
        log.info("[REPORT] Task submitted: id={}, userId={}", task.getId(), userId);

        return task;
    }

    /**
     * 更新任务状态（Consumer 回调）
     */
    public void markProcessing(String taskId) {
        ReportTask task = reportTaskMapper.selectById(taskId);
        if (task != null) {
            task.setStatus(1);  // 1=处理中
            reportTaskMapper.updateById(task);
        }
    }

    /**
     * 完成任务（Python AI 回调）
     */
    public void completeTask(String taskId, String result) {
        ReportTask task = reportTaskMapper.selectById(taskId);
        if (task != null) {
            task.setStatus(2);  // 2=完成
            task.setResult(result);
            reportTaskMapper.updateById(task);
            log.info("[REPORT] Task completed: id={}", taskId);
        }
    }

    /**
     * 任务失败（含重试）
     */
    public void failTask(String taskId, String errorMsg) {
        ReportTask task = reportTaskMapper.selectById(taskId);
        if (task != null) {
            task.setRetryCount(task.getRetryCount() + 1);
            if (task.getRetryCount() >= 3) {
                task.setStatus(3);  // 3=失败
                task.setErrorMessage(errorMsg);
                log.error("[REPORT] Task permanently failed: id={}, error={}", taskId, errorMsg);
            } else {
                task.setStatus(0);  // 重回待处理
                rocketMQTemplate.convertAndSend(TOPIC, taskId);  // 重新投递
                log.warn("[REPORT] Task retry #{}: id={}", task.getRetryCount(), taskId);
            }
            reportTaskMapper.updateById(task);
        }
    }

    public ReportTask getTask(String taskId) {
        return reportTaskMapper.selectById(taskId);
    }
}
