package com.healthmate.controller;

import com.healthmate.entity.Reminder;
import com.healthmate.service.ReminderService;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * 健康提醒接口
 * POST /api/reminders          创建提醒
 * GET  /api/reminders           查询提醒列表
 * DELETE /api/reminders/{id}    取消提醒
 */
@RestController
@RequestMapping("/api/reminders")
@RequiredArgsConstructor
public class ReminderController {

    private final ReminderService reminderService;

    /**
     * 创建提醒
     */
    @PostMapping
    public ResponseEntity<Map<String, Object>> createReminder(@RequestBody ReminderRequest request) {
        Reminder reminder = new Reminder();
        reminder.setUserId(request.getUserId());
        reminder.setContent(request.getContent());
        reminder.setRemindType(request.getRemindType());
        reminder.setScheduledAt(request.getScheduledAt());
        reminder.setIsActive(1);

        reminderService.createReminder(reminder);

        return ResponseEntity.ok(Map.of(
                "id", reminder.getId(),
                "content", reminder.getContent(),
                "scheduledAt", reminder.getScheduledAt().toString(),
                "message", "提醒已创建"
        ));
    }

    /**
     * 查询提醒列表
     */
    @GetMapping
    public ResponseEntity<List<Reminder>> listReminders(@RequestParam Long userId) {
        return ResponseEntity.ok(reminderService.listReminders(userId));
    }

    @Data
    public static class ReminderRequest {
        private Long userId;
        private String content;
        private Integer remindType;    // 0用药 1复查 2运动 3饮食
        private LocalDateTime scheduledAt;
    }
}
