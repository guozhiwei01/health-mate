package com.healthmate.controller;

import com.healthmate.entity.ReportTask;
import com.healthmate.service.ReportService;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * 报告解读接口
 * POST /api/report/submit     提交报告（异步 MQ）
 * GET  /api/report/{id}       查询任务状态
 * POST /internal/report-task/{id}/complete  Python AI 回调
 */
@RestController
@RequiredArgsConstructor
public class ReportController {

    private final ReportService reportService;

    /**
     * 提交报告解读（异步）
     */
    @PostMapping("/api/report/submit")
    public ResponseEntity<Map<String, Object>> submitReport(@RequestBody ReportRequest request) {
        ReportTask task = reportService.submitReport(request.getUserId(), request.getImageUrl());
        return ResponseEntity.ok(Map.of(
                "taskId", task.getId(),
                "status", "processing",
                "message", "报告已提交，正在异步解读中"
        ));
    }

    /**
     * 查询任务状态
     */
    @GetMapping("/api/report/{id}")
    public ResponseEntity<ReportTask> getTask(@PathVariable String id) {
        ReportTask task = reportService.getTask(id);
        if (task == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(task);
    }

    /**
     * Python AI Engine 完成回调（内部接口）
     */
    @PostMapping("/internal/report-task/{id}/complete")
    public ResponseEntity<Map<String, String>> completeTask(
            @PathVariable String id,
            @RequestBody Map<String, String> body) {
        reportService.completeTask(id, body.get("result"));
        return ResponseEntity.ok(Map.of("status", "ok"));
    }

    @Data
    public static class ReportRequest {
        private Long userId;
        private String imageUrl;
    }
}
