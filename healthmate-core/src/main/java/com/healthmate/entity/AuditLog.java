package com.healthmate.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("t_audit_log")
public class AuditLog {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;
    private Long operatorId;
    private String action;
    private String resource;
    private String ipAddr;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
