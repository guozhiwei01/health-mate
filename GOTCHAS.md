# HealthMate 踩坑记录 & 避坑指南

> 开发过程中遇到的环境问题、版本冲突、配置陷阱。下次遇到类似问题直接查这里。

---

## 一、模型加载类

### 1.1 BGE-M3 加载失败：`Unrecognized model`

**症状：**
```
ValueError: Unrecognized model in C:/Users/13203/.cache/huggingface/hub/models--BAAI--bge-m3.
Should have a `model_type` key in its config.json
```

**根因：**
- HuggingFace 缓存目录格式为 `models--BAAI--bge-m3/`，`transformers >= 4.50` 在解析这个目录名时有 bug
- 实际 `config.json` 里 `model_type: xlm-roberta` 是合法的，但目录名匹配逻辑出错

**解决方案：**
```python
# ❌ 不要用缓存根目录
model_path = "C:/Users/13203/.cache/huggingface/hub/models--BAAI--bge-m3"

# ❌ 不要用 HF 名称（离线环境会失败）
model_path = "BAAI/bge-m3"

# ✅ 用 snapshot 完整路径
model_path = "C:/Users/13203/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f..."
```

**查找 snapshot 路径：**
```powershell
Get-ChildItem "C:\Users\13203\.cache\huggingface\hub\models--BAAI--bge-m3\snapshots"
```

### 1.2 BGE-M3 不能用 `SentenceTransformer` 加载

**症状：** 同样的 `Unrecognized model` 错误

**根因：** `sentence_transformers` 内部调 `AutoConfig.from_pretrained()` 时走回了上层缓存目录

**解决方案：** 用原生 `transformers` 直接加载：
```python
from transformers import AutoModel, AutoTokenizer, AutoConfig

config = AutoConfig.from_pretrained(snapshot_path, model_type="xlm-roberta")
tokenizer = AutoTokenizer.from_pretrained(snapshot_path, config=config)
model = AutoModel.from_pretrained(snapshot_path, config=config)
```

### 1.3 BGE-M3 不能用 `XLMRobertaTokenizer`

**症状：**
```
OSError: Not found: "None": No such file or directory Error #2
```

**根因：** BGE-M3 用的是 `sentencepiece.bpe.model`，而 `XLMRobertaTokenizer` 找 `sentencepiece.model`

**解决方案：** 用 `AutoTokenizer`，它会自动选对的 tokenizer class

### 1.4 LoRA 微调模型真实场景不准

**症状：** 合成验证集 97.8%，真实输入 ~33%

**根因：**
- LLM 生成的训练数据偏书面化、偏长句
- 真实用户输入偏口语化、偏短句（3-8 字）
- 验证集和训练集同源（都是 LLM 生成），评估指标虚高

**解决方案：**
- 生产环境用关键词分类器兜底（`intent_lora_path: str = ""`）
- 后续收集真实对话数据重新训练
- 建立独立于训练数据的手工标注测试集

---

## 二、环境配置类

### 2.1 `.env` 覆盖 `config.py` 默认值

**症状：** 明明改了 `config.py`，但运行时还是旧值

**根因：** Pydantic Settings 优先读 `.env` 文件，`.env` 里的值会覆盖代码默认值

**排查方法：**
```python
from app.config import settings
print(settings.embedding_model_path)  # 看实际生效的值
```

**规则：** 改配置时 **同时改 `.env` 和 `config.py`**，或者只在 `.env` 里改

### 2.2 `__pycache__` 导致旧代码生效

**症状：** 改了代码但行为没变

**解决方案：**
```powershell
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
```

### 2.3 Keras 3 与 transformers 冲突

**症状：**
```
ValueError: Your currently installed version of Keras is Keras 3, 
but this is not yet supported in Transformers.
```

**解决方案：**
```bash
pip install tf-keras
# 或者设置环境变量跳过 TF
$env:USE_TF="0"
```

---

## 三、Docker / 中间件类

### 3.1 Docker Desktop 需要手动启动

**症状：** `docker ps` 报错 `failed to connect`

**排查：**
```powershell
Get-Service *docker*  # 看 Status 是否 Running
```

**解决：** 开始菜单 → Docker Desktop → 等鲸鱼图标变绿

### 3.2 Elasticsearch SDK v9 vs ES Server v8

**症状：**
```
BadRequestError(400, 'media_type_header_exception', 
'Accept version must be either version 8 or 7, but found 9')
```

**根因：** `pip install elasticsearch` 默认装最新 v9，但 Docker 里跑的是 ES 8.15.0

**解决方案：**
```bash
pip install "elasticsearch>=8.0,<9.0"
```

### 3.3 Milvus 镜像拉取超时

**症状：** `docker compose up` 卡住或报 `context deadline exceeded`

**解决方案：**
1. 确保 VPN 开启
2. 单独拉取大镜像：`docker pull milvusdb/milvus:v2.5.6`
3. 拉完后再 `docker compose up -d`

### 3.4 ES 8.x API 变更

**症状：** `es.indices.create(body=...)` 报错

**根因：** ES 8.x Python SDK 移除了 `body` 参数

**解决方案：**
```python
# ❌ 旧写法（ES 7.x）
es.indices.create(index="xxx", body={"mappings": {...}})

# ✅ 新写法（ES 8.x）
es.indices.create(index="xxx", mappings={...})
```

---

## 四、FastAPI / 服务类

### 4.1 静态文件挂载覆盖 API 路由

**症状：** `POST /api/chat` 返回 404 或静态文件内容

**根因：** `app.mount("/", StaticFiles(...))` 会拦截所有路径

**解决方案：** 不挂载根路径，用 `FileResponse` 显式返回 `index.html`：
```python
@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")
```

### 4.2 SSE 流式响应前端收不到

**症状：** `EventSource` 或 `fetch` 报 CORS / 连接错误

**检查清单：**
- CORS 中间件是否允许了 `*`
- `Content-Type` 是否为 `text/event-stream`
- 每个 chunk 是否以 `data: ...\n\n` 格式发送

---

## 五、当前环境版本快照

```
Python:              3.10
transformers:        4.52.4
torch:               2.x (CUDA)
pymilvus:            2.5.x
elasticsearch:       8.x (SDK)
Elasticsearch:       8.15.0 (Server)
Milvus:              2.5.6 (Server)
sentence-transformers: 4.x（有兼容问题，不建议用）
peft:                0.x
langchain:           0.3.x
```

---

## 六、通用排查流程

```
代码改了没生效？
  → 清 __pycache__
  → 检查 .env 是否覆盖了 config.py
  → 重启 uvicorn

模型加载失败？
  → 检查路径是否指向 snapshot 目录
  → 检查 transformers 版本兼容性
  → 尝试 AutoModel + AutoConfig(model_type="xxx")

Docker 服务连不上？
  → docker ps 看容器状态
  → docker logs <container> 看错误日志
  → 检查端口是否被占用

Python SDK 报版本错误？
  → pip show <package> 看当前版本
  → 对照服务器版本，安装匹配的 SDK
```
