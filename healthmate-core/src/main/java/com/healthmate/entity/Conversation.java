package com.healthmate.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 会话管理实体
 */
@Data
@TableName("t_conversation")
public class Conversation {

    @TableId(type = IdType.ASSIGN_UUID)
    private String id;

    private Long userId;
    private String title;
    private String lastIntent;
    private Integer messageCount;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;

    @TableLogic
    private LocalDateTime deletedAt;
}
