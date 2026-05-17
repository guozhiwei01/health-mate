# HealthMate · 自训医疗大模型驱动的全栈 AI 健康助手

> 对标蚂蚁阿福 · 完整工程落地 · 开源可复现

---

## 🏗️ 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                      用户端 (Web / App)                      │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTPS
┌───────────────────────────▼─────────────────────────────────┐
│              healthmate-core (Java · :8081)                  │
│  Spring Boot 3 · MyBatis-Plus · Redis · Redisson · RocketMQ │
│  会话管理 · 提醒队列 · 分布式锁 · 审计日志 · 限流            │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP / SSE
┌───────────────────────────▼─────────────────────────────────┐
│             medmate-ai-engine (Python · :8090)               │
│  FastAPI · LangChain · LangGraph · DashScope · BGE-M3       │
│  意图分类 → 五通道路由 → RAG 检索 → 流式推理 → 安全过滤      │
└──────┬────────────┬────────────┬─────────────┬──────────────┘
       │            │            │             │
  ┌────▼────┐ ┌─────▼─────┐ ┌───▼───┐ ┌──────▼──────┐
  │ Milvus  │ │Elasticsearch│ │ Redis │ │  RocketMQ   │
  │ 向量检索 │ │  BM25 检索  │ │ 缓存  │ │  异步管线    │
  └─────────┘ └───────────┘ └───────┘ └─────────────┘
```

## ✨ 核心特性

| 能力 | 实现 |
|------|------|
| 🧠 意图分类 | Qwen2.5-0.5B LoRA 微调，7 类 96% 准确率 |
| 🔀 智能路由 | LangGraph 状态机，五通道（快速/深度/报告/Agent/紧急） |
| 📚 RAG 知识库 | Milvus 向量 + ES BM25 → RRF 融合 → BGE-M3 精排 |
| 🔒 分布式锁 | Redisson tryLock + 看门狗续期 |
| ⏰ 提醒队列 | Redis ZSet + Lua 原子弹出（多实例安全） |
| 📋 异步报告 | RocketMQ → Java Consumer → HTTP → Python AI |
| 🔐 数据安全 | AES-256-GCM 字段加密 + AOP 审计日志 |
| 🚦 限流 | Redis 滑动窗口（用户 10/min + 全局 1000/s） |
| 📊 监控 | Prometheus + Grafana（业务黄金指标） |
| 🌊 流式输出 | SSE 实时推理，Java 透传 Python 流 |

## 🚀 快速启动

### 前置条件

- Docker Desktop
- JDK 17+ (Adoptium)
- Python 3.10+ (Conda)
- Maven 3.9+
- MySQL 8.0 + Redis

### 1. 启动中间件

```bash
# 一键启动 Milvus + ES + RocketMQ + Prometheus + Grafana
docker compose up -d
```

### 2. 初始化数据库

```bash
mysql -u root -proot -e "source deploy/sql/init.sql"
```

### 3. 启动 Python AI Engine

```bash
cd medmate-ai-engine
conda activate health-mate
uvicorn app.main:app --host 0.0.0.0 --port 8090 --reload
```

### 4. 启动 Java Core

```bash
cd healthmate-core
set JAVA_HOME=C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot
mvn spring-boot:run
```

### 5. 访问

| 服务 | 地址 |
|------|------|
| AI Demo 前端 | http://localhost:8090 |
| Java API | http://localhost:8081/api/chat |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (admin/healthmate) |

## 📁 项目结构

```
health-mate/
├── medmate-ai-engine/          # Python AI 引擎
│   ├── app/
│   │   ├── main.py             # FastAPI 入口 + SSE 流式
│   │   ├── intent/             # 意图分类器（LoRA + 关键词混合）
│   │   ├── agent/              # LangGraph 状态机
│   │   ├── models/             # 模型 Provider（DashScope/Ollama）
│   │   ├── rag/                # RAG 检索管线
│   │   └── config.py           # 统一配置
│   ├── training/               # 训练数据 + 微调报告
│   └── static/                 # Demo 前端
│
├── healthmate-core/            # Java 工程层
│   └── src/main/java/com/healthmate/
│       ├── controller/         # REST API（Chat/Report/Reminder）
│       ├── service/            # 业务逻辑（分布式锁/MQ/ZSet）
│       ├── mq/                 # RocketMQ Consumer
│       ├── security/           # AES 加密 + 审计 + 限流
│       ├── entity/             # MyBatis-Plus 实体
│       └── config/             # Prometheus 指标 + 自动填充
│
├── deploy/
│   ├── sql/init.sql            # MySQL DDL（8 张表）
│   ├── prometheus.yml          # Prometheus 抓取配置
│   └── docker-compose-*.yml    # 分组 Docker Compose
│
├── docker-compose.yml          # 全家桶一键启动
├── ARCHITECTURE.md             # 完整技术架构方案
├── GOTCHAS.md                  # 踩坑记录
└── scripts/
    └── test_integration.py     # 全链路集成测试
```

## 🧪 集成测试

```bash
python scripts/test_integration.py
```

```
✅ Python AI Engine 健康检查
✅ Java Core 服务可达
✅ 意图分类 x4
✅ 创建新对话（Java → Python → DashScope）
✅ 继续同一会话
✅ 消息历史查询
✅ 会话列表 + 消息计数
✅ RAG 增强回答
🎉 11/11 全链路集成测试通过！
```

## 📊 技术栈

| 层级 | 技术 |
|------|------|
| **模型层** | Qwen2.5-0.5B LoRA · DashScope API |
| **AI 层** | FastAPI · LangChain · LangGraph · BGE-M3 · Milvus |
| **工程层** | Spring Boot 3 · MyBatis-Plus · Redis · Redisson · RocketMQ |
| **安全** | AES-256-GCM · AOP 审计 · Redis 限流 |
| **可观测** | Prometheus · Grafana · Micrometer |
| **基础设施** | Docker · MySQL 8 · Elasticsearch 8.15 |

## 📄 License

MIT
