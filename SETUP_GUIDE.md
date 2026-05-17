# HealthMate · 本地环境搭建指南

> 硬件：Windows + RTX 4070 Laptop GPU（8GB）
> 目标：本地跑通全链路（微调 + 推理 + Java 工程 + 中间件）
> 最后更新：2026-05-17

---

## 〇、搭建顺序总览

```
Step 1  基础工具（Python / JDK / Docker）        ← 30 分钟
Step 2  Python AI 环境（PyTorch / LLaMA-Factory） ← 1 小时
Step 3  下载模型权重                              ← 看网速
Step 4  中间件 Docker Compose                    ← 15 分钟
Step 5  Java 工程脚手架                          ← 30 分钟
Step 6  验证全链路                               ← 30 分钟
```

---

## 一、基础工具安装

### 1.1 Miniconda（管理 Python 环境）

```powershell
# 下载 Miniconda（官网或清华镜像）
# https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/

# 安装后，打开 Anaconda Prompt，配置清华源加速
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free
conda config --set show_channel_urls yes
```

### 1.2 JDK 17

```powershell
# 推荐用 Eclipse Temurin（免费）
# https://adoptium.net/temurin/releases/?version=17

# 安装后验证
java -version
# 应输出：openjdk version "17.x.x"
```

### 1.3 Maven

```powershell
# 下载：https://maven.apache.org/download.cgi
# 解压到 D:\tools\apache-maven-3.9.x
# 配置环境变量 MAVEN_HOME 和 PATH

mvn -version

# 配置阿里云镜像（加速下载），编辑 conf/settings.xml：
# <mirror>
#   <id>aliyun</id>
#   <mirrorOf>central</mirrorOf>
#   <url>https://maven.aliyun.com/repository/central</url>
# </mirror>
```

### 1.4 Docker Desktop

```powershell
# 下载安装：https://www.docker.com/products/docker-desktop/
# 安装时勾选 WSL 2 backend

# 安装后验证
docker --version
docker compose version

# 配置 Docker Hub 镜像加速（Settings → Docker Engine）
# 添加 "registry-mirrors": ["https://docker.1ms.run"]
```

### 1.5 Git（如果还没装）

```powershell
git --version
# 如果没有：https://git-scm.com/download/win
```

---

## 二、Python AI 环境

### 2.1 创建 Conda 虚拟环境

```powershell
# 创建环境
conda create -n healthmate python=3.10 -y
conda activate healthmate
```

### 2.2 安装 PyTorch（CUDA 版）

```powershell
# 你的驱动是 CUDA 13.0，安装对应的 PyTorch
# 去 https://pytorch.org/get-started/locally/ 查最新命令
# 示例（以 CUDA 12.6 为例，向下兼容）：
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
```

验证 GPU 可用：

```powershell
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
# 应输出：
# True
# NVIDIA GeForce RTX 4070 Laptop GPU
```

### 2.3 安装 LLaMA-Factory（微调框架）

```powershell
cd d:\project
git clone https://github.com/hiyouga/LLaMA-Factory.git
cd LLaMA-Factory
pip install -e ".[torch,metrics,bitsandbytes]"

# bitsandbytes 是 QLoRA 4-bit 量化必需的
# Windows 上如果 bitsandbytes 报错，用：
# pip install bitsandbytes-windows
```

验证安装：

```powershell
llamafactory-cli version
# 应输出版本号，无报错
```

### 2.4 安装 AI 应用层依赖

```powershell
conda activate healthmate

# LangChain 全家桶
pip install langchain langchain-community langgraph langsmith

# FastAPI 服务
pip install fastapi uvicorn[standard]

# 向量数据库 & 检索
pip install pymilvus elasticsearch

# Embedding
pip install sentence-transformers

# vLLM 推理引擎
pip install vllm

# 其他工具
pip install openai httpx pydantic redis rocketmq-client-python
pip install prometheus-client   # 监控指标
```

### 2.5 配置 pip 清华源（加速下载）

```powershell
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 三、下载模型权重

### 3.1 安装 ModelScope CLI

```powershell
pip install modelscope
```

### 3.2 下载模型（建议放在统一目录）

```powershell
# 创建模型存放目录
mkdir D:\models

# ① 意图分类器基座（~1GB，最先下载）
modelscope download --model Qwen/Qwen2.5-0.5B-Instruct --local_dir D:\models\Qwen2.5-0.5B-Instruct

# ② 医疗模型基座（~14GB，QLoRA 微调用）
modelscope download --model Qwen/Qwen2.5-7B --local_dir D:\models\Qwen2.5-7B

# ③ BGE-M3 Embedding（~2GB，RAG 用）
modelscope download --model BAAI/bge-m3 --local_dir D:\models\bge-m3
```

> [!NOTE]
> - 下载走 ModelScope 国内源，速度比 HuggingFace 快很多
> - 0.5B 先下载，几分钟就好，可以马上开始训分类器
> - 7B 比较大，可以晚上挂着下

### 3.3 验证模型可加载

```python
# 快速验证 0.5B 模型
python -c "
from transformers import AutoModelForCausalLM, AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained('D:/models/Qwen2.5-0.5B-Instruct')
model = AutoModelForCausalLM.from_pretrained('D:/models/Qwen2.5-0.5B-Instruct', device_map='auto')
print('✅ 0.5B 模型加载成功，显存占用：', round(model.get_memory_footprint()/1024**3, 2), 'GB')
"
```

---

## 四、中间件 Docker Compose

### 4.1 创建 docker-compose.yml

在项目根目录创建 `docker-compose.yml`：

```yaml
# d:\project\health-mate\docker-compose.yml
version: '3.8'

services:
  # ==================== 核心中间件（先启动这两个） ====================

  mysql:
    image: mysql:8.0
    container_name: hm-mysql
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: healthmate123
      MYSQL_DATABASE: healthmate
      MYSQL_CHARACTER_SET_SERVER: utf8mb4
      MYSQL_COLLATION_SERVER: utf8mb4_unicode_ci
    volumes:
      - mysql_data:/var/lib/mysql
      - ./deploy/sql:/docker-entrypoint-initdb.d   # 初始化 SQL
    command: --default-authentication-plugin=mysql_native_password

  redis:
    image: redis:7-alpine
    container_name: hm-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  # ==================== Week 6-9 再启用 ====================

  # --- RocketMQ ---
  rocketmq-namesrv:
    image: apache/rocketmq:5.3.1
    container_name: hm-rocketmq-namesrv
    ports:
      - "9876:9876"
    command: sh mqnamesrv
    profiles: ["full"]

  rocketmq-broker:
    image: apache/rocketmq:5.3.1
    container_name: hm-rocketmq-broker
    ports:
      - "10911:10911"
    environment:
      NAMESRV_ADDR: rocketmq-namesrv:9876
    command: sh mqbroker -n rocketmq-namesrv:9876
    depends_on:
      - rocketmq-namesrv
    profiles: ["full"]

  # --- Elasticsearch + IK ---
  elasticsearch:
    image: elasticsearch:8.15.0
    container_name: hm-elasticsearch
    ports:
      - "9200:9200"
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    profiles: ["full"]

  # --- Milvus（向量数据库） ---
  milvus:
    image: milvusdb/milvus:v2.4-latest
    container_name: hm-milvus
    ports:
      - "19530:19530"
    volumes:
      - milvus_data:/var/lib/milvus
    environment:
      ETCD_USE_EMBED: "true"
      COMMON_STORAGETYPE: local
    profiles: ["full"]

  # --- MinIO（对象存储） ---
  minio:
    image: minio/minio
    container_name: hm-minio
    ports:
      - "9000:9000"
      - "9001:9001"     # 管理界面
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: healthmate123
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    profiles: ["full"]

  # --- Nacos（服务注册 & 配置） ---
  nacos:
    image: nacos/nacos-server:v2.4.3
    container_name: hm-nacos
    ports:
      - "8848:8848"
      - "9848:9848"
    environment:
      MODE: standalone
      SPRING_DATASOURCE_PLATFORM: ""
      JVM_XMS: 256m
      JVM_XMX: 256m
    profiles: ["full"]

  # --- XXL-Job Admin ---
  xxl-job-admin:
    image: xuxueli/xxl-job-admin:2.4.1
    container_name: hm-xxl-job
    ports:
      - "8088:8080"
    environment:
      SPRING_DATASOURCE_URL: jdbc:mysql://mysql:3306/xxl_job?useUnicode=true&characterEncoding=UTF-8
      SPRING_DATASOURCE_USERNAME: root
      SPRING_DATASOURCE_PASSWORD: healthmate123
    depends_on:
      - mysql
    profiles: ["full"]

  # ==================== 可观测（Week 11 再启用） ====================

  prometheus:
    image: prom/prometheus
    container_name: hm-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./deploy/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
    profiles: ["observability"]

  grafana:
    image: grafana/grafana
    container_name: hm-grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    profiles: ["observability"]

volumes:
  mysql_data:
  redis_data:
  es_data:
  milvus_data:
  minio_data:
```

### 4.2 启动命令

```powershell
# ===== 前期开发（Week 0-5）：只启动 MySQL + Redis =====
docker compose up -d mysql redis

# ===== 工程层开发（Week 6-9）：启动全部中间件 =====
docker compose --profile full up -d

# ===== 可观测（Week 11）：加上监控 =====
docker compose --profile full --profile observability up -d

# ===== 查看状态 =====
docker compose ps

# ===== 停止 =====
docker compose down
```

### 4.3 验证中间件

```powershell
# MySQL
docker exec hm-mysql mysql -uroot -phealthmate123 -e "SELECT 1"

# Redis
docker exec hm-redis redis-cli ping
# 应返回 PONG
```

---

## 五、Java 工程脚手架

### 5.1 创建项目结构

```
d:\project\health-mate\
├── healthmate-gateway/       # 网关服务（8080）
├── healthmate-core/          # 核心业务（8081）
├── healthmate-admin/         # 后台管理（8082）
├── healthmate-common/        # 公共模块
├── medmate-ai-engine/        # Python AI 引擎（8090）
├── deploy/                   # 部署配置
│   ├── sql/                  # 数据库初始化脚本
│   ├── prometheus/
│   └── grafana/
├── docker-compose.yml
├── pom.xml                   # 父 POM
├── ARCHITECTURE.md
├── ENV_SETUP.md
└── SETUP_GUIDE.md            # 本文件
```

### 5.2 父 POM 关键依赖

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.0</version>
</parent>

<properties>
    <java.version>17</java.version>
    <spring-cloud.version>2023.0.3</spring-cloud.version>
    <spring-cloud-alibaba.version>2023.0.1.0</spring-cloud-alibaba.version>
</properties>
```

### 5.3 用 Spring Initializr 快速生成

> https://start.spring.io/
>
> - Project: Maven
> - Language: Java
> - Spring Boot: 3.3.x
> - Java: 17
> - Dependencies: Spring Web, Spring Data JPA, MySQL Driver, Spring Data Redis, Lombok

---

## 六、Python AI 引擎目录

### 6.1 创建目录结构

```powershell
mkdir d:\project\health-mate\medmate-ai-engine
cd d:\project\health-mate\medmate-ai-engine

# 创建目录
mkdir app
mkdir app\intent
mkdir app\models
mkdir app\pipelines
mkdir app\rag
mkdir app\agent
mkdir app\agent\tools
mkdir app\security
mkdir app\utils
mkdir training
mkdir training\data
```

### 6.2 创建 requirements.txt

```
# d:\project\health-mate\medmate-ai-engine\requirements.txt

# === 核心框架 ===
fastapi==0.115.*
uvicorn[standard]==0.32.*

# === AI / LLM ===
langchain>=0.3
langchain-community>=0.3
langgraph>=0.2
langsmith>=0.1
openai>=1.50

# === 向量 & 检索 ===
sentence-transformers>=3.0
pymilvus>=2.4
elasticsearch>=8.15

# === 微调（训练时用） ===
transformers>=4.45
peft>=0.12
bitsandbytes>=0.44
datasets>=3.0
trl>=0.11

# === 推理 ===
vllm>=0.6

# === 中间件客户端 ===
redis>=5.0
httpx>=0.27

# === 监控 ===
prometheus-client>=0.21

# === 工具 ===
pydantic>=2.9
python-multipart>=0.0.9
```

---

## 七、验证全链路（Checklist）

按顺序逐项验证，全部打 ✅ 就说明环境搭好了：

```
[ ] Python 环境
    [ ] conda activate healthmate
    [ ] python --version  →  3.10.x
    [ ] python -c "import torch; print(torch.cuda.is_available())"  →  True

[ ] LLaMA-Factory
    [ ] llamafactory-cli version  →  无报错

[ ] 模型权重
    [ ] D:\models\Qwen2.5-0.5B-Instruct 目录存在且有文件
    [ ] 快速加载验证通过（见 3.3 节）

[ ] Docker 中间件
    [ ] docker compose up -d mysql redis
    [ ] docker exec hm-mysql mysql -uroot -phealthmate123 -e "SELECT 1"  →  1
    [ ] docker exec hm-redis redis-cli ping  →  PONG

[ ] Java
    [ ] java -version  →  17.x.x
    [ ] mvn -version  →  3.9.x

[ ] FastAPI 冒烟测试
    [ ] 在 medmate-ai-engine/app/ 下创建 main.py：
        from fastapi import FastAPI
        app = FastAPI(title="HealthMate AI Engine")

        @app.get("/health")
        def health(): return {"status": "ok"}
    [ ] uvicorn app.main:app --port 8090
    [ ] 浏览器访问 http://localhost:8090/health  →  {"status":"ok"}
    [ ] 访问 http://localhost:8090/docs  →  Swagger UI 正常
```

---

## 八、常见问题

### Q1: bitsandbytes Windows 安装失败

```powershell
# Windows 上 bitsandbytes 官方包可能报错，用社区 Windows 版：
pip install bitsandbytes-windows
# 或者用 conda 安装：
conda install -c conda-forge bitsandbytes
```

### Q2: CUDA out of memory（训练时）

```
# 关掉所有吃显存的程序（浏览器、微信等）
# 训练配置确认这几项：
quantization_bit: 4
per_device_train_batch_size: 1
gradient_checkpointing: true
cutoff_len: 512
```

### Q3: Docker 拉镜像慢

```powershell
# Docker Desktop → Settings → Docker Engine → 添加镜像源：
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
# 保存后 Docker 自动重启
```

### Q4: ModelScope 下载慢 / 中断

```powershell
# 方法 1：设置环境变量用国内 CDN
$env:MODELSCOPE_CACHE="D:\models"

# 方法 2：用 Git LFS 直接 clone（支持断点续传）
git lfs install
git clone https://www.modelscope.cn/Qwen/Qwen2.5-0.5B-Instruct.git D:\models\Qwen2.5-0.5B-Instruct
```

### Q5: PyTorch 版本和 CUDA 版本怎么对应？

```
你的驱动 CUDA 版本：13.0（向下兼容）
PyTorch CUDA 版本：装 cu126 即可（不需要和驱动完全一致，低于驱动版本就行）
```

---

## 九、下一步

环境搭好后，按 14 周计划推进：

| 阶段 | 做什么 | 前置条件 |
|------|--------|---------|
| **Week 0-1** | 标注意图分类数据（800 条） | Python + LLaMA-Factory 就绪 |
| **Week 2** | 训练 0.5B 意图分类器 | 数据 + 模型权重就绪 |
| **Week 3-4** | 7B QLoRA 医疗微调 | 0.5B 训练跑通 |
| **Week 5** | vLLM 部署 + 调度器联调 | 微调模型就绪 |
| **Week 6** | Java 单体 + FastAPI 端到端 | Docker MySQL + Redis |
| **Week 7** | LangGraph + RAG | Milvus + ES 启动 |
| **Week 8-10** | Java 微服务 + 工程难点 | 全部中间件启动 |
