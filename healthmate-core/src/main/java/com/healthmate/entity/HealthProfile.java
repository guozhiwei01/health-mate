package com.healthmate.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 健康档案实体
 */
@Data
@TableName("t_health_profile")
public class HealthProfile {

    @TableId(type = IdType.AUTO)
    private Long id;

    private Long userId;
    private String name;
    private LocalDate birthday;
    private byte[] phoneEnc;    // AES 加密存储

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;

    @TableLogic
    private LocalDateTime deletedAt;
}
