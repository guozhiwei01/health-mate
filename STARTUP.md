# HealthMate 启动/停止手册

## 一键启动（按顺序）

### 1. Docker 中间件

```bash
# 必需：Nacos + MySQL(小皮面板) + Redis 需要先启动
docker start hm-nacos

# 按需启动（开发哪个模块就启哪个）
docker start rmqnamesrv rmqbroker          # RocketMQ（报告管线）
docker start milvus-etcd milvus-minio milvus-standalone  # Milvus（RAG）
docker start elasticsearch                 # ES（RAG BM25）
docker start hm-prometheus hm-grafana      # 监控
```

### 2. Python AI Engine

```bash
cd d:\project\health-mate\medmate-ai-engine
conda activate health-mate
uvicorn app.main:app --host 0.0.0.0 --port 8090 --reload
```

### 3. Java Core

```bash
cd d:\project\health-mate\healthmate-core
set JAVA_HOME=C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot
mvn spring-boot:run
```

### 4. Java Gateway（可选，走网关才需要）

```bash
cd d:\project\health-mate\healthmate-gateway
set JAVA_HOME=C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot
mvn spring-boot:run
```

## 访问地址

| 服务 | 端口 | 说明 |
|------|:----:|------|
| Gateway | 8888 | API 入口（JWT 鉴权） |
| Java Core | 8081 | 业务服务 |
| Python AI | 8090 | AI 推理 |
| Nacos | 8848 | 服务注册中心 |
| Prometheus | 9090 | 指标采集 |
| Grafana | 3001 | 监控面板 (admin/healthmate) |
| RocketMQ | 9876 | 消息队列 |

## 一键停止

```bash
# Java
taskkill /IM java.exe /F

# Docker 全停
docker stop hm-nacos rmqnamesrv rmqbroker milvus-standalone milvus-minio milvus-etcd elasticsearch hm-prometheus hm-grafana
```
