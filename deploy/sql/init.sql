-- HealthMate 数据库初始化脚本
-- 对应 ARCHITECTURE.md v2.0 数据库设计

CREATE DATABASE IF NOT EXISTS healthmate
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE healthmate;

-- 用户健康档案
CREATE TABLE IF NOT EXISTS t_health_profile (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id     BIGINT UNIQUE NOT NULL,
    name        VARCHAR(64),
    birthday    DATE,
    phone_enc   VARBINARY(256)          COMMENT '手机号 AES 加密',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at  DATETIME NULL           COMMENT '软删除',
    INDEX idx_user (user_id)
) COMMENT '用户健康档案';

-- 慢性病史
CREATE TABLE IF NOT EXISTS t_user_condition (
    id           BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id      BIGINT NOT NULL,
    `condition`  VARCHAR(64)             COMMENT '糖尿病/高血压/...',
    diagnosed_at DATE,
    deleted_at   DATETIME NULL,
    INDEX idx_user (user_id),
    INDEX idx_condition (`condition`)
) COMMENT '慢性病史';

-- 对话消息
CREATE TABLE IF NOT EXISTS t_message (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    conversation_id VARCHAR(64),
    role            VARCHAR(16)             COMMENT 'user/assistant/system',
    content         TEXT                    COMMENT 'AES 加密存储',
    model           VARCHAR(64),
    input_tokens    INT,
    output_tokens   INT,
    latency_ms      INT,
    trace_id        VARCHAR(64),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted_at      DATETIME NULL,
    INDEX idx_conv (conversation_id)
) COMMENT '对话消息';

-- 报告解读任务
CREATE TABLE IF NOT EXISTS t_report_task (
    id            VARCHAR(64) PRIMARY KEY,
    user_id       BIGINT NOT NULL,
    image_url     VARCHAR(512),
    status        TINYINT DEFAULT 0       COMMENT '0待处理 1处理中 2完成 3失败',
    result        TEXT                    COMMENT 'AES 加密存储',
    error_message TEXT                    COMMENT '失败原因',
    retry_count   INT DEFAULT 0,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted_at    DATETIME NULL,
    INDEX idx_user (user_id)
) COMMENT '报告解读任务';

-- 审计日志
CREATE TABLE IF NOT EXISTS t_audit_log (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id     BIGINT,
    operator_id BIGINT                  COMMENT '操作者',
    action      VARCHAR(64)             COMMENT 'READ_PROFILE / UPDATE_RECORD / ...',
    resource    VARCHAR(128)            COMMENT '被访问的资源',
    ip_addr     VARCHAR(45),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_time (user_id, created_at DESC)
) COMMENT '审计日志';

-- 紧急事件日志
CREATE TABLE IF NOT EXISTS t_emergency_log (
    id               BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id          BIGINT NOT NULL,
    trigger_content  TEXT                COMMENT '触发内容（脱敏后）',
    notified_members JSON               COMMENT '已通知家庭成员',
    nearby_hospitals JSON               COMMENT '推荐附近医院',
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id)
) COMMENT '紧急事件日志';

-- 会话管理
CREATE TABLE IF NOT EXISTS t_conversation (
    id              VARCHAR(64) PRIMARY KEY,
    user_id         BIGINT NOT NULL,
    title           VARCHAR(128)            COMMENT '会话标题（自动生成）',
    last_intent     VARCHAR(32)             COMMENT '最近意图',
    message_count   INT DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at      DATETIME NULL,
    INDEX idx_user (user_id),
    INDEX idx_updated (updated_at DESC)
) COMMENT '会话管理';

-- 健康提醒
CREATE TABLE IF NOT EXISTS t_reminder (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id         BIGINT NOT NULL,
    content         VARCHAR(256)            COMMENT '提醒内容',
    remind_type     TINYINT DEFAULT 0       COMMENT '0用药 1复查 2运动 3饮食',
    cron_expr       VARCHAR(64)             COMMENT 'cron 表达式（周期性）',
    scheduled_at    DATETIME                COMMENT '下次触发时间',
    is_active       TINYINT DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    deleted_at      DATETIME NULL,
    INDEX idx_user (user_id),
    INDEX idx_scheduled (scheduled_at)
) COMMENT '健康提醒';
