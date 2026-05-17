package com.healthmate.security;

import com.healthmate.entity.AuditLog;
import com.healthmate.mapper.AuditLogMapper;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

/**
 * 审计日志 AOP 切面
 * 自动记录所有 @Audited 方法的调用到 t_audit_log
 *
 * 面试要点：
 * - 医疗系统合规要求：所有数据读写必须可追溯
 * - AOP 实现零侵入，不影响业务代码
 * - 记录：谁(userId) + 什么时候 + 做了什么(action) + 访问了什么(resource) + 从哪里(IP)
 */
@Slf4j
@Aspect
@Component
@RequiredArgsConstructor
public class AuditAspect {

    private final AuditLogMapper auditLogMapper;

    @Around("@annotation(audited)")
    public Object audit(ProceedingJoinPoint joinPoint, Audited audited) throws Throwable {
        // 执行原方法
        Object result = joinPoint.proceed();

        // 异步记录审计日志（不影响主流程性能）
        try {
            AuditLog auditLog = new AuditLog();
            auditLog.setAction(audited.action());
            auditLog.setResource(audited.resource().isEmpty()
                    ? joinPoint.getSignature().getDeclaringType().getSimpleName()
                    : audited.resource());

            // 从请求中提取 userId 和 IP
            ServletRequestAttributes attrs =
                    (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attrs != null) {
                HttpServletRequest request = attrs.getRequest();
                auditLog.setIpAddr(getClientIp(request));
                // userId 从 header 或参数中获取（简化版）
                String userId = request.getParameter("userId");
                if (userId != null) {
                    auditLog.setUserId(Long.parseLong(userId));
                    auditLog.setOperatorId(Long.parseLong(userId));
                }
            }

            auditLogMapper.insert(auditLog);
            log.debug("[AUDIT] {} {} from {}",
                    audited.action(), auditLog.getResource(), auditLog.getIpAddr());
        } catch (Exception e) {
            // 审计失败不影响业务
            log.warn("[AUDIT] Failed to record: {}", e.getMessage());
        }

        return result;
    }

    private String getClientIp(HttpServletRequest request) {
        String ip = request.getHeader("X-Forwarded-For");
        if (ip == null || ip.isEmpty()) {
            ip = request.getHeader("X-Real-IP");
        }
        if (ip == null || ip.isEmpty()) {
            ip = request.getRemoteAddr();
        }
        return ip;
    }
}
