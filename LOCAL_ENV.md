# HealthMate · 本地环境清单

> 最后验证时间：2026-05-17
> 操作系统：Windows

---

## 一、硬件

| 项目 | 详情 |
|------|------|
| **GPU** | NVIDIA GeForce RTX 4070 Laptop GPU |
| **显存** | 8 GB GDDR6 |
| **驱动版本** | 581.83 |
| **CUDA 驱动版本** | 13.0（向下兼容） |

---

## 二、基础工具

| 工具 | 版本 | 安装位置 |
|------|------|---------|
| **Python** | 3.10.11 | `C:\Users\13203\AppData\Local\Programs\Python\Python310` |
| **pip** | 26.1.1 | 随 Python |
| **Git** | 2.46.0 | 系统 PATH |
| **Docker Desktop** | 29.2.1 | 系统 PATH |
| **Docker Compose** | v5.0.2 | 随 Docker Desktop |
| **JDK 17** | OpenJDK 17.0.19 Temurin | `C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot` |
| **Maven** | 3.9.9 | `D:\apache-maven-3.9.9` |
| **Node.js** | v23.8.0 | 系统 PATH |
| **Ollama** | 0.24.0 | 系统 PATH |

> **注意**：JDK 17 的 JAVA_HOME 已设置为用户环境变量，新终端窗口生效。
> Maven 需要 JAVA_HOME，请确保新终端中 `java -version` 输出 17.x。

---

## 三、Python AI 工具链

### 3.1 深度学习框架

| 包 | 版本 | 说明 |
|---|------|------|
| **torch** | 2.7.1+cu118 | CUDA 版，GPU 加速 ✅ |
| **torchvision** | 0.22.1+cu118 | |
| **torchaudio** | 2.7.1+cu118 | |
| **accelerate** | 1.7.0 | 分布式训练 |

**GPU 验证**：

```python
import torch
print(torch.cuda.is_available())           # True
print(torch.cuda.get_device_name(0))       # NVIDIA GeForce RTX 4070 Laptop GPU
```

### 3.2 微调框架

| 包 | 版本 | 说明 |
|---|------|------|
| **llamafactory** | 0.9.3 | LLaMA-Factory 微调框架 |
| **peft** | 0.15.2 | LoRA / QLoRA 适配器 |
| **bitsandbytes** | 0.49.2 | 4-bit / 8-bit 量化 |
| **transformers** | 4.52.4 | HuggingFace 模型加载 |
| **datasets** | 3.6.0 | 训练数据加载 |

> **注意**：运行 LLaMA-Factory 前需设置环境变量 `USE_TF=0`（跳过 TensorFlow 检查）。
>
> PowerShell：`$env:USE_TF="0"`
>
> 或设为永久用户环境变量（已配置）。

### 3.3 AI 应用层

| 包 | 版本 | 说明 |
|---|------|------|
| **langchain-core** | 1.3.3 | LangChain 核心 |
| **langchain-openai** | 1.2.1 | OpenAI 兼容调用 |
| **langgraph** | 1.1.10 | 状态图编排 |
| **fastapi** | 0.136.1 | Python HTTP 服务 |
| **uvicorn** | 0.46.0 | ASGI 服务器 |
| **openai** | 2.32.0 | OpenAI SDK（调 Ollama / vLLM） |
| **httpx** | 0.28.1 | HTTP 客户端 |

---

## 四、中间件

| 中间件 | 版本 | 状态 | 位置 |
|--------|------|:----:|------|
| **Redis** | 5.0.14 | ✅ 运行中 | `D:\redis\Redis-x64-5.0.14.1` |
| **MySQL** | — | ⏳ 待 Docker 启动 | docker-compose.yml |
| **RocketMQ** | — | ⏳ Week 6-9 启用 | docker-compose.yml |
| **Elasticsearch** | — | ⏳ Week 6-9 启用 | docker-compose.yml |
| **Milvus** | — | ⏳ Week 6-9 启用 | docker-compose.yml |
| **MinIO** | — | ⏳ Week 6-9 启用 | docker-compose.yml |
| **Nacos** | — | ⏳ Week 6-9 启用 | docker-compose.yml |
| **XXL-Job** | — | ⏳ Week 6-9 启用 | docker-compose.yml |

---

## 五、模型资源

| 模型 | 状态 | 位置 |
|------|:----:|------|
| **BGE-M3**（Embedding，768 维） | ✅ 已缓存 | `C:\Users\13203\.cache\huggingface\hub\models--BAAI--bge-m3` |
| **Qwen2.5-0.5B-Instruct**（意图分类器基座） | ⏳ 待下载 | 计划放 `D:\models\` |
| **Qwen2.5-7B**（医疗模型基座，本地 QLoRA） | ⏳ 待下载 | 计划放 `D:\models\` |

---

## 六、推理引擎

| 引擎 | 版本 | 说明 |
|------|------|------|
| **Ollama** | 0.24.0 | Windows 原生支持，替代 vLLM |
| **vLLM** | — | 不支持 Windows，不使用 |

Ollama 暴露 OpenAI 兼容 API（`http://localhost:11434/v1`），上层代码与 vLLM 调用方式一致。

---

## 七、环境变量

| 变量 | 值 | 作用域 |
|------|------|------|
| **JAVA_HOME** | `C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot` | 用户 |
| **USE_TF** | `0` | 用户（跳过 TensorFlow） |
| **PATH** （新增） | `%JAVA_HOME%\bin` | 用户 |

---

## 八、已知限制 & 注意事项

1. **显存 8GB**：9B 模型 QLoRA 训练需关闭浏览器等吃显存进程，配置 `gradient_checkpointing: true` + `cutoff_len: 512`
2. **本地推荐用 7B 模型**验证训练流程，9B 正式训练可上云 GPU
3. **双模型无法同时部署**（显存不够），本地开发时单模型运行
4. **vLLM 不支持 Windows**，使用 Ollama 替代，API 兼容
5. **Maven 依赖 JAVA_HOME**，需在新终端窗口中使用（环境变量需重新加载）
