package com.healthmate.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 健康提醒实体
 */
@Data
@TableName("t_reminder")
public class Reminder {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;
    private String content;
    private Integer remindType;     // 0用药 1复查 2运动 3饮食
    private String cronExpr;
    private LocalDateTime scheduledAt;
    private Integer isActive;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableLogic
    private LocalDateTime deletedAt;
}
