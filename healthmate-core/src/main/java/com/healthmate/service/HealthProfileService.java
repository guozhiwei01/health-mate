package com.healthmate.service;

import com.healthmate.entity.HealthProfile;
import com.healthmate.mapper.HealthProfileMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;
import org.springframework.stereotype.Service;

import java.util.concurrent.TimeUnit;

/**
 * 健康档案 Service
 * - Redisson 分布式锁防止并发覆盖
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class HealthProfileService {

    private final HealthProfileMapper healthProfileMapper;
    private final RedissonClient redissonClient;

    /**
     * 更新健康档案（带分布式锁）
     * 防止多端同时修改导致数据覆盖
     */
    public void updateProfile(Long userId, HealthProfile updated) {
        String lockKey = "health:record:lock:" + userId;
        RLock lock = redissonClient.getLock(lockKey);

        try {
            // 等待 3 秒获取锁，持有 10 秒（看门狗自动续期）
            if (!lock.tryLock(3, 10, TimeUnit.SECONDS)) {
                throw new RuntimeException("操作太频繁，请稍后重试");
            }

            // 查 → 合并 → 写（三步原子）
            HealthProfile existing = healthProfileMapper.selectByUserId(userId);
            if (existing == null) {
                updated.setUserId(userId);
                healthProfileMapper.insert(updated);
                log.info("[PROFILE] Created profile for user: {}", userId);
            } else {
                // 合并非空字段
                if (updated.getName() != null) existing.setName(updated.getName());
                if (updated.getBirthday() != null) existing.setBirthday(updated.getBirthday());
                healthProfileMapper.updateById(existing);
                log.info("[PROFILE] Updated profile for user: {}", userId);
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("锁获取被中断", e);
        } finally {
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }

    public HealthProfile getProfile(Long userId) {
        return healthProfileMapper.selectByUserId(userId);
    }
}
