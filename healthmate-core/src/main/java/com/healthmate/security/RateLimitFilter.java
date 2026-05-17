package com.healthmate.security;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

/**
 * 用户级 + 全局限流 Filter
 *
 * 面试要点（对标 Sentinel）：
 * - 用户级：每用户 10 次/分钟（滑动窗口，Redis INCR + EXPIRE）
 * - 全局级：1000 次/秒（简单令牌桶）
 * - 生产环境可替换为 Sentinel @SentinelResource 注解
 * - 当前实现是轻量版，原理一致
 */
@Slf4j
@Component
public class RateLimitFilter implements Filter {

    private final StringRedisTemplate redisTemplate;

    private static final int USER_LIMIT = 10;         // 每用户 10 次/分钟
    private static final int USER_WINDOW_SECONDS = 60;
    private static final int GLOBAL_LIMIT = 1000;      // 全局 1000 次/秒
    private static final String GLOBAL_KEY = "rate:global";

    public RateLimitFilter(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {

        HttpServletRequest httpReq = (HttpServletRequest) request;
        String path = httpReq.getRequestURI();

        // 只限流 /api/ 接口
        if (!path.startsWith("/api/")) {
            chain.doFilter(request, response);
            return;
        }

        // 1. 全局限流
        String globalKey = GLOBAL_KEY + ":" + (System.currentTimeMillis() / 1000);
        Long globalCount = redisTemplate.opsForValue().increment(globalKey);
        if (globalCount != null && globalCount == 1) {
            redisTemplate.expire(globalKey, 2, TimeUnit.SECONDS);
        }
        if (globalCount != null && globalCount > GLOBAL_LIMIT) {
            reject((HttpServletResponse) response, "系统繁忙，请稍后重试", 503);
            return;
        }

        // 2. 用户级限流
        String userId = httpReq.getParameter("userId");
        if (userId == null) {
            // 从 body 中无法直接取（需要包装 request），跳过
            chain.doFilter(request, response);
            return;
        }

        String userKey = "rate:user:" + userId;
        Long userCount = redisTemplate.opsForValue().increment(userKey);
        if (userCount != null && userCount == 1) {
            redisTemplate.expire(userKey, USER_WINDOW_SECONDS, TimeUnit.SECONDS);
        }
        if (userCount != null && userCount > USER_LIMIT) {
            log.warn("[RATE-LIMIT] User {} exceeded limit: {}/{}", userId, userCount, USER_LIMIT);
            reject((HttpServletResponse) response, "请求太频繁，请稍后再试", 429);
            return;
        }

        chain.doFilter(request, response);
    }

    private void reject(HttpServletResponse response, String message, int status) throws IOException {
        response.setStatus(status);
        response.setContentType("application/json;charset=UTF-8");
        response.getWriter().write(
                "{\"code\":" + status + ",\"message\":\"" + message + "\"}"
        );
    }
}
