package com.healthmate.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.healthmate.entity.HealthProfile;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface HealthProfileMapper extends BaseMapper<HealthProfile> {

    @Select("SELECT * FROM t_health_profile WHERE user_id = #{userId} AND deleted_at IS NULL")
    HealthProfile selectByUserId(Long userId);
}
