# HealthMate · 项目骨架方案

> 基于 ARCHITECTURE.md v2.0，对应 Week 0 的项目初始化
> 请审阅后确认，我再动手创建文件

---

## 一、整体目录结构

```
d:\project\health-mate\
│
├── 📄 pom.xml                          # Maven 父 POM（聚合模块）
├── 📄 docker-compose.yml               # 中间件编排
├── 📄 .gitignore
├── 📄 README.md
│
├── 📁 healthmate-common/               # 公共模块（工具类、通用实体）
│   ├── pom.xml
│   └── src/main/java/com/healthmate/common/
│       ├── exception/
│       │   ├── BizException.java           # 业务异常
│       │   └── GlobalExceptionHandler.java # 全局异常处理
│       ├── response/
│       │   └── R.java                      # 统一返回体 R<T>
│       ├── config/
│       │   └── RedisConfig.java            # Redis 序列化配置
│       ├── security/
│       │   └── FieldEncryptor.java         # AES-256-GCM 字段加密
│       └── util/
│           └── TraceUtil.java              # X-Trace-Id 工具
│
├── 📁 healthmate-gateway/              # 网关服务（8080）
│   ├── pom.xml
│   └── src/main/
│       ├── java/com/healthmate/gateway/
│       │   ├── GatewayApplication.java
│       │   ├── filter/
│       │   │   ├── AuthFilter.java         # JWT 鉴权
│       │   │   └── TraceFilter.java        # 链路追踪 ID 注入
│       │   └── config/
│       │       └── RouteConfig.java        # 路由配置
│       └── resources/
│           ├── application.yml
│           └── bootstrap.yml               # Nacos 配置
│
├── 📁 healthmate-core/                 # 核心业务服务（8081）
│   ├── pom.xml
│   └── src/main/
│       ├── java/com/healthmate/core/
│       │   ├── CoreApplication.java
│       │   │
│       │   ├── controller/
│       │   │   ├── ChatController.java         # 对话接口（SSE 流式）
│       │   │   ├── HealthProfileController.java# 健康档案 CRUD
│       │   │   ├── ReportController.java       # 报告上传 & 查询
│       │   │   └── ReminderController.java     # 提醒管理
│       │   │
│       │   ├── service/
│       │   │   ├── ChatService.java
│       │   │   ├── HealthProfileService.java
│       │   │   ├── ReportService.java
│       │   │   ├── ReminderService.java        # Redis ZSet + Lua
│       │   │   └── AiEngineClient.java         # 调 Python AI 引擎
│       │   │
│       │   ├── entity/
│       │   │   ├── HealthProfile.java
│       │   │   ├── UserCondition.java
│       │   │   ├── Message.java
│       │   │   ├── ReportTask.java
│       │   │   ├── AuditLog.java
│       │   │   └── EmergencyLog.java
│       │   │
│       │   ├── mapper/                         # MyBatis-Plus Mapper
│       │   │   ├── HealthProfileMapper.java
│       │   │   ├── MessageMapper.java
│       │   │   ├── ReportTaskMapper.java
│       │   │   └── AuditLogMapper.java
│       │   │
│       │   ├── mq/
│       │   │   ├── ReportConsumer.java          # RocketMQ 消费 → HTTP 转 Python
│       │   │   └── ReminderPushConsumer.java
│       │   │
│       │   ├── job/
│       │   │   └── ReminderScheduleJob.java    # XXL-Job 定时扫描
│       │   │
│       │   └── config/
│       │       ├── RedissonConfig.java         # Redisson 分布式锁
│       │       ├── SentinelConfig.java         # 限流配置
│       │       └── RocketMQConfig.java
│       │
│       └── resources/
│           ├── application.yml
│           ├── bootstrap.yml
│           └── mapper/                          # MyBatis XML（如需要）
│
├── 📁 healthmate-admin/                # 后台管理服务（8082）
│   ├── pom.xml
│   └── src/main/
│       ├── java/com/healthmate/admin/
│       │   ├── AdminApplication.java
│       │   ├── controller/
│       │   │   └── DashboardController.java    # 数据大盘
│       │   └── service/
│       │       └── AnalyticsService.java       # ES 聚合分析
│       └── resources/
│           └── application.yml
│
├── 📁 medmate-ai-engine/               # Python AI 引擎（8090）
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                         # FastAPI 入口
│   │   ├── config.py                       # 配置（模型路径、Redis 地址等）
│   │   ├── dispatcher.py                   # ★ 调度核心（四条路径）
│   │   │
│   │   ├── intent/
│   │   │   ├── __init__.py
│   │   │   ├── classifier.py               # 意图分类器（0.5B LoRA）
│   │   │   └── schemas.py                  # IntentResult（Top-2 输出）
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                     # 抽象 ModelProvider
│   │   │   ├── qwen_fast.py                # 快速通道（Ollama 调用）
│   │   │   ├── healthmate_med.py           # 深度通道（微调模型）
│   │   │   └── router.py                   # 灰度路由逻辑
│   │   │
│   │   ├── pipelines/
│   │   │   ├── __init__.py
│   │   │   └── report_pipeline.py          # 报告解读三阶段管线
│   │   │
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   ├── medical_kb.py               # 知识库管理
│   │   │   ├── chunker.py                  # 医学文档切分
│   │   │   ├── retriever.py                # BM25 + 向量混合检索
│   │   │   └── reranker.py                 # BGE-M3 Reranker
│   │   │
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── health_graph.py             # LangGraph 状态图
│   │   │   ├── memory.py                   # 上下文压缩
│   │   │   └── tools/
│   │   │       ├── __init__.py
│   │   │       ├── reminder_tool.py
│   │   │       ├── record_tool.py
│   │   │       ├── drug_search_tool.py
│   │   │       └── emergency_tool.py
│   │   │
│   │   ├── security/
│   │   │   ├── __init__.py
│   │   │   ├── pii_filter.py               # 日志脱敏
│   │   │   └── content_guard.py            # 输出安全检查
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── metrics.py                  # Prometheus 指标
│   │       └── tracing.py                  # 链路追踪
│   │
│   └── training/                           # 微调训练脚本
│       ├── data/
│       │   └── medical_4k/                 # 训练数据目录
│       ├── configs/
│       │   ├── intent_classifier.yaml      # 0.5B 分类器训练配置
│       │   └── medical_sft.yaml            # 7B 医疗模型训练配置
│       ├── train_intent_classifier.py
│       ├── train_medical.py
│       └── evaluate.py
│
└── 📁 deploy/                          # 部署配置
    ├── sql/
    │   └── init.sql                        # 数据库初始化（6 张表）
    ├── prometheus/
    │   └── prometheus.yml
    └── grafana/
        └── dashboards/
```

---

## 二、Java 模块关系

```
healthmate-parent (pom.xml)              # 父 POM，管版本
├── healthmate-common                    # 公共依赖，被其他模块引用
├── healthmate-gateway → common          # 网关
├── healthmate-core   → common           # 核心业务
└── healthmate-admin  → common           # 后台管理
```

### 父 POM 关键版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| Spring Boot | 3.3.0 | 父 POM parent |
| Spring Cloud | 2023.0.3 | Gateway / OpenFeign |
| Spring Cloud Alibaba | 2023.0.1.0 | Nacos / Sentinel / RocketMQ |
| MyBatis-Plus | 3.5.7 | ORM |
| Redisson | 3.35.0 | 分布式锁 |
| Java | 17 | 编译版本 |

---

## 三、Python 入口文件说明

### `app/main.py` — FastAPI 入口

```python
# 暴露的核心接口：
POST /api/intent/classify        # 意图分类
POST /api/chat/stream            # 流式对话（SSE）
POST /internal/report/analyze    # 报告异步解读（Java 内部调用）
GET  /health                     # 健康检查
GET  /metrics                    # Prometheus 指标
```

### `app/dispatcher.py` — 调度核心

```python
# 四条路径：
# 1. emergency_handler   → 紧急处理
# 2. report_pipeline     → 独立报告管线
# 3. agent_executor      → Agent 工具调用
# 4. model_35b / model_med → 快速/深度通道
```

---

## 四、数据库（6 张表）

`deploy/sql/init.sql` 包含：

| 表名 | 说明 |
|------|------|
| `t_health_profile` | 用户健康档案（敏感字段 AES 加密） |
| `t_user_condition` | 慢性病史（拆表，支持按病种查询） |
| `t_message` | 对话消息（加密存储，含 token 计费） |
| `t_report_task` | 报告解读任务（含重试和错误信息） |
| `t_audit_log` | 审计日志（医疗合规） |
| `t_emergency_log` | 紧急事件日志（家庭通知记录） |

---

## 五、各模块初始文件内容

骨架阶段每个文件只写**最小可运行代码**（能启动、能调通），具体业务逻辑后续按周计划填充。

### Java 侧

| 文件 | 内容 |
|------|------|
| `*Application.java` | `@SpringBootApplication` 启动类 |
| `Controller` | 空接口定义 + `@RequestMapping` |
| `Service` | 接口 + 空实现 |
| `Entity` | 字段定义 + Lombok `@Data` |
| `Mapper` | MyBatis-Plus `BaseMapper` 继承 |
| `application.yml` | 端口 + 数据源 + Redis 连接 |

### Python 侧

| 文件 | 内容 |
|------|------|
| `main.py` | FastAPI app + 3 个路由（空壳） |
| `config.py` | Pydantic Settings 配置类 |
| `dispatcher.py` | route() 函数骨架 |
| `classifier.py` | 类定义 + `classify()` 方法签名 |
| `health_graph.py` | LangGraph 状态定义 + 空节点 |
| 其他 `*.py` | 类定义 + TODO 注释 |

---

## 六、骨架完成后的验证目标

```
[ ] Java Gateway  启动成功，访问 http://localhost:8080/actuator/health → UP
[ ] Java Core     启动成功，访问 http://localhost:8081/actuator/health → UP
[ ] Java Admin    启动成功，访问 http://localhost:8082/actuator/health → UP
[ ] Python Engine 启动成功，访问 http://localhost:8090/health → {"status": "ok"}
[ ] Python Docs   访问 http://localhost:8090/docs → Swagger UI
[ ] MySQL         docker exec hm-mysql mysql ... → 6 张表存在
[ ] 跨语言调通    Java Core → HTTP → Python Engine /health → 200
```

---

## 七、需要你确认的问题

> 看完后告诉我：

1. **ORM 选择**：用 **MyBatis-Plus** 还是 **Spring Data JPA**？（架构文档里两种都提了，我倾向 MyBatis-Plus，更灵活）
2. **包名**：用 `com.healthmate` 可以吗？
3. **目录位置**：所有模块都放在 `d:\project\health-mate\` 下？
4. **先创建哪些**：先全部创建？还是先 Python + 一个 Java 单体，后面再拆微服务？
