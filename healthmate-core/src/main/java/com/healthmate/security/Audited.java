package com.healthmate.security;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * 审计日志注解
 * 标注在 Controller/Service 方法上，自动记录操作日志
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Audited {
    String action();                // READ_PROFILE / UPDATE_RECORD / SUBMIT_REPORT / ...
    String resource() default "";   // 资源类型
}
