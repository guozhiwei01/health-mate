# HealthMate · 环境准备总览

> 基于 ARCHITECTURE.md v2.0 整理，按分层 + 优先级排列
> 最后更新：2026-05-17

---

## 一、Python AI 引擎侧（`medmate-ai-engine`）

| 工具 | 版本建议 | 用途 |
|------|---------|------|
| **Python** | 3.10+ | AI 引擎运行时 |
| **CUDA / NPU 驱动** | 昇腾 CANN 8.x 或 CUDA 12.x | 模型训练 & 推理（本地开发可先用 CUDA） |
| **PyTorch** | 2.x（需支持 BF16） | 训练框架 |
| **DeepSpeed** | 最新版 | 分布式训练加速（ZeRO Stage 2） |
| **vLLM** | 最新版 | 模型推理服务（昇腾用 vLLM-Ascend） |
| **LLaMA-Factory** | 最新版 | LoRA 微调 Qwen3.5-9B / Qwen2.5-0.5B |
| **LangChain + LangGraph** | 最新版 | AI 应用编排、状态图 |
| **FastAPI + Uvicorn** | 最新版 | Python HTTP 服务（端口 8090） |
| **BGE-M3** | - | Embedding 模型（768 维，本地部署） |

> [!NOTE]
> **本地开发**：如果没有昇腾 910B，先用 NVIDIA GPU（建议 ≥ 24GB 显存，如 4090）+ CUDA 做开发调试，部署时再切昇腾。

---

## 二、Java 工程层（`healthmate-gateway / core / admin`）

| 工具 | 版本建议 | 用途 |
|------|---------|------|
| **JDK** | 17+ | Spring Boot 3 硬性要求 |
| **Maven** 或 **Gradle** | 最新版 | Java 项目构建 |
| **Spring Boot** | 3.x | 核心框架 |
| **Spring Cloud** | 2022.x+ | 微服务全家桶（Gateway / OpenFeign / Sentinel） |
| **Redisson** | 最新版 | 分布式锁客户端 |
| **IntelliJ IDEA** | - | Java 开发 IDE（推荐） |

---

## 三、中间件（Docker Compose 统一管理）

> [!TIP]
> 强烈建议写一个 `docker-compose.yml` 把以下中间件全部纳管，一键 `docker compose up -d` 拉起本地开发环境。

| 中间件 | 版本建议 | 端口 | 用途 |
|--------|---------|------|------|
| **MySQL** | 8.x | 3306 | 业务数据库（6 张核心表） |
| **Redis** | 7.x | 6379 | 会话状态、ZSet 提醒队列、分布式锁、灰度配置 |
| **RocketMQ** | 5.x | 9876/10911 | 异步消息（report-analyze / reminder-push / diary-summary） |
| **Elasticsearch** | 8.x | 9200 | BM25 医学知识检索 + IK 中文分词 + 行为聚合 |
| **Milvus** | 2.x | 19530 | 向量数据库（768 维 HNSW 索引，存 RAG chunk） |
| **MinIO** | 最新版 | 9000 | 对象存储（报告图片） |
| **Nacos** | 2.x | 8848 | 服务注册 & 配置中心 |
| **XXL-Job Admin** | 2.4+ | 8088 | 分布式定时任务调度中心 |

---

## 四、可观测 & DevOps

| 工具 | 用途 |
|------|------|
| **Docker + Docker Compose** | 容器化部署 & 本地环境编排 |
| **Prometheus** | 指标采集（技术指标 + 业务黄金指标） |
| **Grafana** | 监控大盘（5 个面板：概览/路由/AI 质量/资源/合规） |
| **SkyWalking** | 跨语言链路追踪（Java + Python，X-Trace-Id 串联） |
| **LangSmith** | AI 质量评估（需注册账号，100 条评估集） |

---

## 五、模型 & 数据资源（提前下载）

| 资源 | 大小估计 | 用途 | 优先级 |
|------|---------|------|--------|
| **Qwen2.5-0.5B-Instruct** | ~1 GB | 意图分类器基座（7 类，LoRA 微调） | ⭐ 最先下载 |
| **Qwen3.5-9B** | ~18 GB | 深度通道基座（HealthMate-Med-9B 微调） | ⭐⭐ |
| **Qwen3.6-35B-A3B（AWQ 量化）** | ~18 GB | 快速通道 + 多模态视觉提取 | ⭐⭐ |
| **BGE-M3** | ~2 GB | Embedding 模型（中文，768 维） | ⭐⭐ |
| **医疗训练数据** | 4000 条 | 自行标注（ShareGPT 格式，7:2:1 划分） | Week 0-1 准备 |
| **MedBench 评测集** | - | 模型评测（CMB-Exam / CMB-Clin） | Week 3-4 使用 |

> [!IMPORTANT]
> 模型下载建议使用 [ModelScope](https://modelscope.cn) 国内镜像加速，或者用 `huggingface-cli download` + HF Mirror 代理。

---

## 六、推荐启动顺序（对应 Week 0-1）

```
Step 1 ─ 基础工具
    ├── 安装 Python 3.10+
    ├── 安装 JDK 17+
    └── 安装 Docker Desktop

Step 2 ─ 中间件
    └── docker-compose 拉起 MySQL + Redis（最小集合，其余按需加）

Step 3 ─ 模型准备
    ├── 下载 Qwen2.5-0.5B-Instruct（小，先练手）
    └── 配置 GPU 环境（PyTorch + CUDA / CANN）

Step 4 ─ 验证
    ├── vLLM 跑通 Qwen2.5-0.5B 推理
    └── FastAPI Hello World 跑通

Step 5 ─ 数据准备
    └── 标注意图分类训练数据（800-1000 条，7 类，ShareGPT 格式）
```

---

## 七、最小可用环境（快速上手）

> [!TIP]
> 如果想先**最小化跑起来**验证架构可行性，只需要以下组合：

| 层 | 只需装 |
|----|--------|
| Python | Python 3.10 + FastAPI + LangChain |
| Java | JDK 17 + Spring Boot 3 |
| 中间件 | Docker：MySQL + Redis |
| GPU | 一张显卡，先拿 Qwen2.5-0.5B 做分类器实验 |

其余中间件（RocketMQ、ES、Milvus、Nacos、XXL-Job 等）可在 **Week 6-9 工程层阶段**逐步接入，不影响前期模型训练和 AI 应用层开发。

---

## 八、硬件需求参考

| 场景 | 最低配置 | 推荐配置 |
|------|---------|---------|
| 本地开发调试 | 16GB 内存 + 单卡 8GB GPU | 32GB 内存 + 单卡 24GB GPU（4090） |
| 模型训练（LoRA） | 单卡 24GB（9B 模型 BF16 + LoRA） | 双卡 24GB + DeepSpeed ZeRO-2 |
| 完整部署（双模型） | 昇腾 910B × 1（64GB HBM） | 昇腾 910B × 2（分别部署 35B 和 9B） |
| 中间件（Docker） | 8GB 内存 + 50GB 磁盘 | 16GB 内存 + 100GB SSD |
