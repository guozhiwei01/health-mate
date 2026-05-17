package com.healthmate.service;

import com.healthmate.entity.Reminder;
import com.healthmate.mapper.ReminderMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.Collections;
import java.util.List;

/**
 * 健康提醒 Service
 * - Redis ZSet 优先级队列
 * - Lua 原子弹出（防止多实例重复消费）
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ReminderService {

    private final ReminderMapper reminderMapper;
    private final StringRedisTemplate redisTemplate;

    private static final String REMINDER_QUEUE = "reminder:queue";

    /**
     * Lua 原子脚本：取出 + 删除（防止多实例重复消费）
     */
    private static final String LUA_ATOMIC_POP = """
            local tasks = redis.call('ZRANGEBYSCORE', KEYS[1], 0, ARGV[1])
            if #tasks > 0 then
                redis.call('ZREM', KEYS[1], unpack(tasks))
            end
            return tasks
            """;

    /**
     * 创建提醒并加入 Redis 队列
     */
    public Reminder createReminder(Reminder reminder) {
        reminderMapper.insert(reminder);

        // 加入 Redis ZSet（score = 触发时间的 epoch 秒）
        if (reminder.getScheduledAt() != null) {
            double score = reminder.getScheduledAt()
                    .toEpochSecond(ZoneOffset.of("+8"));
            redisTemplate.opsForZSet().add(
                    REMINDER_QUEUE,
                    reminder.getId().toString(),
                    score
            );
            log.info("[REMINDER] Scheduled: id={}, time={}", reminder.getId(), reminder.getScheduledAt());
        }
        return reminder;
    }

    /**
     * 每分钟扫描到期提醒（Lua 原子弹出）
     */
    @Scheduled(fixedRate = 60_000)
    public void processDueReminders() {
        long windowEnd = System.currentTimeMillis() / 1000 + 60;

        DefaultRedisScript<List> script = new DefaultRedisScript<>(LUA_ATOMIC_POP, List.class);
        @SuppressWarnings("unchecked")
        List<String> dueTasks = redisTemplate.execute(
                script,
                Collections.singletonList(REMINDER_QUEUE),
                String.valueOf(windowEnd)
        );

        if (dueTasks != null && !dueTasks.isEmpty()) {
            log.info("[REMINDER] Processing {} due reminders", dueTasks.size());
            for (String taskId : dueTasks) {
                try {
                    pushReminder(Long.parseLong(taskId));
                } catch (Exception e) {
                    log.error("[REMINDER] Failed to push reminder {}: {}", taskId, e.getMessage());
                }
            }
        }
    }

    /**
     * 推送提醒（后续对接 WebSocket / 推送服务）
     */
    private void pushReminder(Long reminderId) {
        Reminder reminder = reminderMapper.selectById(reminderId);
        if (reminder == null || reminder.getIsActive() == 0) return;

        log.info("[REMINDER-PUSH] userId={}, content={}",
                reminder.getUserId(), reminder.getContent());

        // TODO: 对接推送服务（WebSocket / FCM / 微信模板消息）
    }

    /**
     * 获取用户的提醒列表
     */
    public List<Reminder> listReminders(Long userId) {
        return reminderMapper.selectList(
                new com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper<Reminder>()
                        .eq(Reminder::getUserId, userId)
                        .eq(Reminder::getIsActive, 1)
                        .orderByAsc(Reminder::getScheduledAt)
        );
    }
}
