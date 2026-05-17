package com.healthmate.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 报告解读任务实体
 */
@Data
@TableName("t_report_task")
public class ReportTask {

    @TableId(type = IdType.ASSIGN_UUID)
    private String id;

    private Long userId;
    private String imageUrl;
    private Integer status;       // 0待处理 1处理中 2完成 3失败
    private String result;
    private String errorMessage;
    private Integer retryCount;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;

    @TableLogic
    private LocalDateTime deletedAt;
}
