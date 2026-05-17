# HealthMate · 完整技术架构方案

> 对标蚂蚁阿福的开源个人健康 AI 助手
> 自训医疗大模型 + 双模型调度 + 全栈工程落地
> 版本：v2.0 | 状态：设计阶段（已通过架构评审）

---

## 一、项目定位

### 一句话

**HealthMate** 是一个对标蚂蚁阿福的开源个人健康 AI 助手，核心差异在于：
不使用任何第三方医疗 AI API， **完全自训医疗大模型驱动** ，在昇腾 910B 集群上部署，
同时具备 **完整的生产级工程能力** （Spring Cloud 微服务 + Redis + MQ + ES）。

### 和蚂蚁阿福的对比定位

| 能力     | 蚂蚁阿福               | HealthMate                         |
| -------- | ---------------------- | ---------------------------------- |
| 多轮问诊 | ✅                     | ✅                                 |
| 报告解读 | ✅                     | ✅                                 |
| 药品识别 | ✅                     | ✅                                 |
| 健康陪伴 | ✅                     | ✅                                 |
| 模型来源 | 蚂蚁医疗大模型（闭源） | **自训开源医疗模型**         |
| 调度机制 | 未公开                 | **双模型路由（公开可复现）** |
| 代码开源 | ❌                     | ✅ GitHub 完整开源                 |
| 部署算力 | 阿里云                 | **华为昇腾 910B（国产化）**  |

---

## 二、三层模型架构（核心设计）

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────────┐
│  Layer 1：意图分类器                              │
│  Qwen2.5-0.5B（LoRA 微调，医疗意图分类）           │
│  延迟 < 50ms，输出：Top-2 意图 + 置信度            │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  Layer 2：模型调度器（FastAPI）                   │
│  意图 + 置信度 + 上下文轮数 → 四条路径             │
└──┬──────────┬──────────┬────────────┬───────────┘
   │          │          │            │
   ▼          ▼          ▼            ▼
快速通道   深度通道   报告管线     Agent/紧急
35B-A3B   14B Med   独立Pipeline  工具调用
   │          │          │            │
   └──────────┴──────────┴────────────┘
                    │
                    ▼
         安全检查 → 输出 / 降级
```

### 2.1 Layer 1：意图分类器

 **模型选择** ：Qwen2.5-0.5B-Instruct（LoRA 微调）

 **意图类别设计（7类）** ：

```python
INTENT_LABELS = {
    "casual_chat":     "日常闲聊",        # → 快速通道
    "health_qa":       "健康知识问答",     # → 快速通道
    "symptom_consult": "症状自述/咨询",   # → 深度通道
    "drug_consult":    "用药咨询",        # → 深度通道
    "report_parse":    "报告解读",        # → 独立报告管线（见 2.4）
    "emergency":       "紧急情况",        # → 紧急处理器
    "task_command":    "任务型指令",       # → Agent 工具调用
}
```

 **混合意图处理** （解决"我头疼，能吃布洛芬吗"这类多意图）：

```python
# 分类器输出 Top-2，不再是单标签
class IntentResult:
    primary_intent: str        # 主意图
    primary_confidence: float
    secondary_intent: str      # 次要意图（可为 None）
    secondary_confidence: float

# 调度时取医疗优先级更高的意图
INTENT_PRIORITY = {
    "emergency": 0, "symptom_consult": 1, "drug_consult": 2,
    "report_parse": 3, "task_command": 4, "health_qa": 5, "casual_chat": 6
}

def resolve_intent(result: IntentResult) -> str:
    if result.secondary_intent and result.secondary_confidence > 0.4:
        # 取优先级更高的意图路由
        return min([result.primary_intent, result.secondary_intent],
                   key=lambda x: INTENT_PRIORITY[x])
    return result.primary_intent
```

 **训练数据** （800-1000 条，每类 100-200 条，ShareGPT 格式）

 **评估目标** ：准确率 ≥ 95%

### 2.2 Layer 2：模型调度器（四条路径，全文统一）

> ⚠️ v1.0 中报告解读路由存在三处不一致，v2.0 统一为四条独立路径。

```python
def route(intent: str, confidence: float, turn_count: int) -> str:

    # 路径 1：紧急处理（最高优先级，直接返回）
    if intent == "emergency":
        return "emergency_handler"

    # 路径 2：报告解读（独立管线，不走快速/深度通道）
    # 内部编排：35B-A3B 视觉提取 → RAG 检索 → 14B 生成解读
    if intent == "report_parse":
        return "report_pipeline"

    # 路径 3：Agent 工具调用
    if intent == "task_command":
        return "agent_executor"

    # 路径 4A：快速通道（35B-A3B）
    if intent in ["casual_chat", "health_qa"] and confidence > 0.85:
        return "model_35b_a3b"

    # 路径 4B：深度通道（14B Med）
    if intent in ["symptom_consult", "drug_consult"]:
        return "model_14b_med"

    # 多轮追问自动升级
    if turn_count > 5:
        return "model_14b_med"

    return "model_35b_a3b"
```

 **熔断与降级** ：

* 35B-A3B 连续被追问 → 升级到 14B
* 14B 超时（> 30s）→ 降级到 35B-A3B + "建议就医"提示
* 两个模型均不可用 → 预设免责声明 + 推荐就诊

 **会话状态（Redis Hash）** ：

```python
session = {
    "session_id":    "xxx",
    "user_id":       "123",
    "history":       "[...]",
    "current_model": "14b_med",
    "turn_count":    7,
    "last_intent":   "symptom_consult",
    # 超过 10 轮后压缩（见 2.5 上下文压缩策略）
    "context_summary": { ... }
}
# TTL: 3600s
```

### 2.3 快速通道：Qwen3.6-35B-A3B

 **选型理由** ：MoE 激活 3B，推理 < 200ms；原生多模态；Q4 量化 ~18GB 显存。

 **承接场景** ：健康科普、日常闲聊、多模态图片初步识别（不含深度解读）

 **部署** ：

```bash
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen3.6-35B-A3B \
    --port 8001 \
    --tensor-parallel-size 1 \
    --quantization awq \
    --max-model-len 32768 \
    --enable-thinking false \
    --dtype bfloat16
```

### 2.4 深度通道：HealthMate-Med（微调模型）

 **基座** ：Qwen3.5-9B（稠密，2026 年 2 月发布，替代原方案中的 Qwen2.5-14B）

 **为什么改用 Qwen3.5-9B** ：

* MMLU-Pro 82.5 分，超越 Qwen3-30B（80.9）
* 稠密架构，LoRA 微调效果优于 MoE
* BF16 推理约 18GB，比 14B 省 40% 显存
* 2026 年新架构（混合注意力），比 Qwen2.5-14B 新一整代

 **训练数据（4000 条 · 7:2:1）** ：

```
训练集 2800 条：
├── 症状问诊多轮对话  1200 条  ← 模拟医生追问风格
├── 报告解读文本      600 条  ← 异常指标→解读（文本部分，视觉由35B负责）
├── 用药咨询          500 条  ← 适应症/禁忌/副作用/相互作用
├── 安全兜底          300 条  ← "请立即就医"场景
└── 慢病管理          200 条  ← 糖尿病/高血压日常管理

验证集 800 条 | 测试集 400 条（+ MedBench 公开评测集）
```

 **训练配置** ：

```yaml
model_name_or_path: Qwen/Qwen3.5-9B
finetuning_type: lora
lora_rank: 8
lora_alpha: 16
lora_target: q_proj,v_proj,k_proj,o_proj
per_device_train_batch_size: 2
gradient_accumulation_steps: 4
learning_rate: 5.0e-5
num_train_epochs: 3
lr_scheduler_type: cosine
bf16: true
deepspeed: examples/deepspeed/ds_z2_config.json
output_dir: saves/HealthMate-Med-9B/lora/sft
```

> ⚠️ 昇腾 910B4 对 Qwen3.5-9B 混合注意力架构的支持需在 Week 0 确认兼容性。
> 若不兼容，回退到 Qwen3-8B 稠密版（昇腾支持已成熟）。

### 2.5 独立报告管线（v2.0 新增，解决路由矛盾）

报告解读不走快速/深度通道，独立为三阶段管线：

```python
# report_pipeline.py
async def report_pipeline(image: bytes, session: HealthState) -> str:

    # 阶段 1：35B-A3B 视觉理解（利用其多模态能力）
    # 输出：结构化的异常发现（不做医学解读）
    visual_findings = await model_35b_a3b.extract_report_findings(image)
    # 示例输出：{"abnormal_items": ["LDL 4.8 偏高", "血糖 7.2 偏高"], ...}

    # 阶段 2：RAG 检索相关医学知识
    # 用提取出的异常项目检索参考资料
    context = await rag.search(visual_findings["abnormal_items"])

    # 阶段 3：14B Med 生成专业解读
    # 基于视觉发现 + RAG 上下文，生成带引用的解读
    report = await model_14b_med.generate_report_interpretation(
        findings=visual_findings,
        rag_context=context
    )
    return report
```

 **LangGraph 状态图中的路由** （全文统一为四条路径）：

```python
workflow.add_conditional_edges(
    "route_model",
    lambda s: s["selected_model"],
    {
        "model_35b_a3b":   "fast_inference",
        "model_14b_med":   "retrieve_context",   # 先 RAG 再推理
        "report_pipeline": "report_pipeline",    # 独立管线
        "agent_executor":  "agent_execute",
        "emergency_handler": "emergency_handle"
    }
)
```

### 2.6 上下文压缩策略（医疗安全设计）

医疗对话不能随意摘要压缩，漏掉症状可能导致判断错误。
超过 10 轮后采用**结构化提取 + 保留关键轮**的方式：

```python
class MedicalContextSummary(BaseModel):
    chief_complaint: str              # 主诉："头痛两天"
    symptoms: list[str]               # 已确认症状
    denied_symptoms: list[str]        # 明确否认的症状（"没有恶心"）
    medications: list[str]            # 当前用药
    allergies: list[str]              # 过敏史（本轮提及）
    key_turn_indices: list[int]       # 保留原文的关键轮次（如第1、3、7轮）
    summary_text: str                 # 给模型看的文本摘要

# 关键轮判断标准：包含新症状、否认症状、用药信息的轮次
def is_key_turn(turn: dict) -> bool:
    keywords = ["症状", "不舒服", "疼", "吃", "药", "过敏", "没有", "否认"]
    return any(kw in turn["content"] for kw in keywords)
```

### 2.7 模型版本管理与灰度发布

每次迭代微调出新版模型，按灰度切换，不直接替换：

```python
# Redis 存储灰度配置（可热更新）
model_routing_config = {
    "14b_med": {
        "v1": {"weight": 0.9, "endpoint": "http://vllm-v1:8002/v1"},
        "v2": {"weight": 0.1, "endpoint": "http://vllm-v2:8003/v1"},
    }
}

def select_model_endpoint(model_name: str, user_id: int) -> str:
    """按 user_id hash 稳定分流，同一用户始终用同一版本"""
    config = get_config_from_redis(model_name)
    bucket = hash(str(user_id)) % 100
    cumulative = 0
    for version, cfg in config.items():
        cumulative += cfg["weight"] * 100
        if bucket < cumulative:
            return cfg["endpoint"]
```

 **发布流程** ：灰度 10% → LangSmith 对比评估 → 无问题 → 全量切换 → 保留旧版 24h 可回滚

---

## 三、应用层架构（LangChain + LangGraph）

### 3.1 目录结构

```
medmate-ai-engine/
├── app/
│   ├── main.py
│   ├── dispatcher.py                 # ★ 调度核心（四条路径）
│   │
│   ├── intent/
│   │   ├── classifier.py
│   │   └── schemas.py                # IntentResult（Top-2 输出）
│   │
│   ├── models/
│   │   ├── base.py                   # 抽象 Provider
│   │   ├── qwen_35b_a3b.py
│   │   ├── healthmate_med.py         # 微调模型（含版本路由）
│   │   └── router.py                 # 灰度路由逻辑
│   │
│   ├── pipelines/                    # ★ 独立管线（v2.0 新增）
│   │   └── report_pipeline.py        # 报告解读三阶段管线
│   │
│   ├── rag/
│   │   ├── medical_kb.py
│   │   ├── chunker.py                # 医学文档切分策略（见 3.4）
│   │   ├── retriever.py              # BM25 + 向量混合检索
│   │   └── reranker.py               # BGE-M3 Reranker
│   │
│   ├── agent/
│   │   ├── health_graph.py           # LangGraph 状态图（含错误处理）
│   │   ├── tools/
│   │   │   ├── reminder_tool.py      # 调 Java Reminder Service
│   │   │   ├── record_tool.py        # 记录健康数据
│   │   │   ├── drug_search_tool.py   # 药品查询
│   │   │   └── emergency_tool.py     # 紧急情况（含家庭通知）
│   │   └── memory.py
│   │
│   ├── security/                     # ★ 安全模块（v2.0 新增）
│   │   ├── pii_filter.py             # 日志脱敏
│   │   └── content_guard.py          # 输出安全检查
│   │
│   └── utils/
│       ├── metrics.py                # Prometheus（含业务黄金指标）
│       └── tracing.py
│
└── training/
    ├── data/medical_4k/
    ├── train_intent_classifier.py
    ├── train_medical_9b.py
    └── evaluate.py
```

### 3.2 LangGraph 状态图（含错误处理，v2.0 完整版）

```python
class HealthState(TypedDict):
    user_input: str
    intent: str
    confidence: float
    turn_count: int
    selected_model: str
    rag_context: list
    response: str
    safety_flag: bool
    error: str | None              # v2.0 新增：错误信息

# 节点定义
workflow.add_node("classify_intent",   classify_intent_node)
workflow.add_node("route_model",       route_model_node)
workflow.add_node("retrieve_context",  retrieve_context_node)
workflow.add_node("fast_inference",    fast_inference_node)
workflow.add_node("deep_inference",    deep_inference_node)
workflow.add_node("report_pipeline",   report_pipeline_node)   # v2.0
workflow.add_node("agent_execute",     agent_execute_node)
workflow.add_node("emergency_handle",  emergency_handle_node)
workflow.add_node("safety_check",      safety_check_node)
workflow.add_node("fallback_response", fallback_node)          # v2.0：降级节点
workflow.add_node("blocked_response",  blocked_node)           # v2.0：拦截节点

# 入口
workflow.set_entry_point("classify_intent")
workflow.add_edge("classify_intent", "route_model")

# 路由到四条路径
workflow.add_conditional_edges(
    "route_model",
    lambda s: s["selected_model"],
    {
        "model_35b_a3b":     "fast_inference",
        "model_14b_med":     "retrieve_context",
        "report_pipeline":   "report_pipeline",
        "agent_executor":    "agent_execute",
        "emergency_handler": "emergency_handle",
    }
)
workflow.add_edge("retrieve_context", "deep_inference")

# v2.0：推理失败走降级而不是直接挂
workflow.add_conditional_edges(
    "deep_inference",
    lambda s: "safety_check" if s.get("response") else "fallback_response",
    {"safety_check": "safety_check", "fallback_response": "fallback_response"}
)
workflow.add_conditional_edges(
    "fast_inference",
    lambda s: "safety_check" if s.get("response") else "fallback_response",
    {"safety_check": "safety_check", "fallback_response": "fallback_response"}
)

# v2.0：安全拦截不直接到 END
workflow.add_conditional_edges(
    "safety_check",
    lambda s: END if not s["safety_flag"] else "blocked_response",
    {END: END, "blocked_response": "blocked_response"}
)

workflow.add_edge("report_pipeline",   "safety_check")
workflow.add_edge("agent_execute",     "safety_check")
workflow.add_edge("emergency_handle",  END)
workflow.add_edge("fallback_response", END)
workflow.add_edge("blocked_response",  END)

health_app = workflow.compile(checkpointer=redis_checkpointer)
```

### 3.3 RAG 知识库

```python
# 混合检索（权重：BM25 0.3 + 向量 0.7）
from langchain.retrievers import EnsembleRetriever

ensemble = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.3, 0.7]
)
# → BGE-M3 Reranker 精排 Top 5 → 带引用的 RAG Chain
```

### 3.4 知识库工程（v2.0 新增）

 **文档切分策略** （医学文档特化）：

```python
# 医学文档不能简单按字数切分，要按语义单元
# 优先级：章节 > 段落 > 句子

from langchain.text_splitter import RecursiveCharacterTextSplitter

medical_splitter = RecursiveCharacterTextSplitter(
    separators=["\n## ", "\n### ", "\n\n", "\n", "。"],
    chunk_size=512,
    chunk_overlap=64,           # 64 token overlap 保证上下文连贯
    length_function=token_count
)
# 化验单/表格：保留完整表格为一个 chunk，不切分
```

 **Embedding 模型** ：BGE-M3（支持中文，768 维，本地部署）

 **增量更新** ：新文档入库走 RocketMQ 异步管线，不阻塞查询。

 **索引结构** ：

```
Milvus Collection: medical_kb
  - chunk_id (PK)
  - doc_id (关联 MySQL t_document)
  - vector (768 dim, HNSW 索引)
  - text (原文, max 512 token)
  - metadata (来源/章节/更新时间)

ES Index: medical_kb
  - 同一批 chunk 同步写入
  - IK 中文分词，BM25 检索
```

### 3.5 RocketMQ Python 侧方案（v2.0 修正）

> v1.0 中 Python 直接消费 RocketMQ，SDK 稳定性差。v2.0 改为 Java 消费后 HTTP 转发。

```
报告异步解读流程：

用户上传 → Java Chat Service → 存 MinIO → 投 RocketMQ
                                                ↓
                                    Java Report Consumer（消费）
                                                ↓
                                    HTTP POST /internal/report/analyze
                                                ↓
                                    Python AI Engine（处理）
                                                ↓
                                    HTTP POST /internal/report-task/{id}/complete
                                                ↓
                                    Java Chat Service → SSE 推送用户
```

**Python 侧**只暴露 HTTP 接口，无需 MQ SDK：

```python
@app.post("/internal/report/analyze")
async def analyze_report(req: ReportAnalyzeRequest):
    result = await report_pipeline(req.image_url, req.task_id)
    # 完成后回调 Java
    await http_client.post(
        f"{JAVA_CHAT_URL}/internal/report-task/{req.task_id}/complete",
        json={"result": result}
    )
    return {"status": "processing"}
```

---

## 四、Java 工程层

### 4.1 微服务拆分（精简为 3 个核心服务，面试时讲清楚比 5 个浅的更有说服力）

| 服务               | 端口 | 职责                               | 覆盖面试题                            |
| ------------------ | ---- | ---------------------------------- | ------------------------------------- |
| healthmate-gateway | 8080 | 网关、鉴权、限流、链路追踪         | Spring Cloud Gateway、Sentinel        |
| healthmate-core    | 8081 | 用户、会话、提醒、健康档案（合并） | 分布式锁、Redis ZSet、MQ、ES、XXL-Job |
| healthmate-admin   | 8082 | 后台、数据分析、租户管理           | ES 聚合、Grafana                      |
| medmate-ai-engine  | 8090 | Python AI 引擎                     | 跨语言通信                            |

> 面试说明：微服务按业务边界拆分，healthmate-core 目前合并了用户/会话/提醒/档案，
> 如果流量上来可以按"读多写少"维度进一步拆分——这体现了渐进式拆分的工程思维，
> 比一开始就拆 5 个服务更真实。

### 4.2 七个面试问题落地（与 v1.0 相同，保留）

#### ① 分布式锁（健康档案并发写 + 配额扣减）

```java
// 健康档案并发写防覆盖
RLock lock = redisson.getLock("health:record:lock:" + userId);
try {
    if (!lock.tryLock(3, 10, TimeUnit.SECONDS)) {
        throw new BizException("操作太频繁");
    }
    // 查 → 合并 → 写（三步原子）
} finally {
    if (lock.isHeldByCurrentThread()) lock.unlock();
}
```

#### ② Redis ZSet 提醒队列（v2.0 修复竞态条件）

> v1.0 中 rangeByScore + remove 非原子，多实例部署会重复消费。v2.0 改为 Lua 脚本。

```java
@Scheduled(fixedRate = 60_000)
public void processDueReminders() {
    long windowEnd = System.currentTimeMillis() / 1000 + 60;

    // v2.0：Lua 原子弹出，防止多实例重复消费
    String luaScript = """
        local tasks = redis.call('ZRANGEBYSCORE', KEYS[1], 0, ARGV[1])
        if #tasks > 0 then
            redis.call('ZREM', KEYS[1], unpack(tasks))
        end
        return tasks
    """;
    List<String> dueTasks = redisTemplate.execute(
        new DefaultRedisScript<>(luaScript, List.class),
        List.of("reminder:queue"),
        String.valueOf(windowEnd)
    );

    for (String taskId : dueTasks) {
        mqTemplate.convertAndSend("reminder-push-topic",
            new ReminderPushMsg(taskId));
    }
}

// 添加提醒（紧急事件提前触发）
public void scheduleReminder(Reminder reminder) {
    double score = reminder.getScheduledTime().toEpochSecond();
    if (reminder.isUrgent()) score -= 300;  // 提前 5 分钟
    redisTemplate.opsForZSet().add("reminder:queue",
        reminder.getId().toString(), score);
}
```

 **面试答法（直接讲）** ：

> "我专门处理了多实例部署下的竞态——用 Lua 脚本原子地'取出并删除'，
> 保证同一任务不会被两个实例同时消费。这个细节体现了对分布式并发的真实思考。"

#### ③ RocketMQ（报告异步解读管线）

```java
// Java Consumer 消费 MQ，HTTP 转发给 Python
@RocketMQMessageListener(topic = "report-analyze-topic",
                          consumerGroup = "report-consumer")
public class ReportConsumer implements RocketMQListener<ReportAnalyzeMsg> {
    @Override
    public void onMessage(ReportAnalyzeMsg msg) {
        // HTTP 转发到 Python AI Engine
        aiEngineClient.analyzeReport(
            new ReportAnalyzeRequest(msg.getTaskId(), msg.getImageUrl())
        );
    }
}
```

#### ④ ES（医学知识检索 + 行为分析）

```java
// 热门症状聚合分析（后台大盘）
SearchRequest request = new SearchRequest("chat_logs");
request.source(new SearchSourceBuilder()
    .aggregation(AggregationBuilders.terms("top_intents")
        .field("intent.keyword").size(20))
);
```

#### ⑤ Spring Cloud 全家桶（Gateway + Nacos + OpenFeign + Sentinel）

#### ⑥ XXL-Job 分布式定时（千万级提醒按 user_id 分片）

#### ⑦ Sentinel 限流（用户级 10 次/分钟，全局 1000 次/秒）

### 4.3 数据库设计（v2.0 修正版）

```sql
-- 用户健康档案
CREATE TABLE t_health_profile (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id     BIGINT UNIQUE NOT NULL,
    name        VARCHAR(64),
    birthday    DATE,
    -- 敏感字段 AES 加密存储（见安全设计章节）
    phone_enc   VARBINARY(256),
    created_at  DATETIME,
    updated_at  DATETIME,
    deleted_at  DATETIME NULL,       -- v2.0：软删除（医疗数据不物理删除）
    INDEX idx_user (user_id)
);

-- 慢性病史（v2.0：从 JSON 拆为关联表，支持按病种查询）
CREATE TABLE t_user_condition (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id     BIGINT NOT NULL,
    condition   VARCHAR(64),         -- 糖尿病/高血压/...
    diagnosed_at DATE,
    deleted_at  DATETIME NULL,
    INDEX idx_user (user_id),
    INDEX idx_condition (condition)  -- 支持按病种查询
);

-- 对话消息（v2.0：拆分 token 计费字段）
CREATE TABLE t_message (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    conversation_id VARCHAR(64),
    role            VARCHAR(16),
    content         TEXT,            -- AES 加密存储
    model           VARCHAR(64),
    input_tokens    INT,             -- v2.0：输入/输出分开计
    output_tokens   INT,
    latency_ms      INT,
    trace_id        VARCHAR(64),
    created_at      DATETIME,
    deleted_at      DATETIME NULL,   -- v2.0：软删除
    INDEX idx_conv (conversation_id)
);

-- 报告解读任务（v2.0：加错误信息和重试）
CREATE TABLE t_report_task (
    id            VARCHAR(64) PRIMARY KEY,
    user_id       BIGINT NOT NULL,
    image_url     VARCHAR(512),
    status        TINYINT,           -- 0待处理 1处理中 2完成 3失败
    result        TEXT,              -- AES 加密存储
    error_message TEXT,              -- v2.0：失败原因
    retry_count   INT DEFAULT 0,     -- v2.0：重试次数
    created_at    DATETIME,
    deleted_at    DATETIME NULL,
    INDEX idx_user (user_id)
);

-- 审计日志（v2.0 新增：医疗合规必需）
CREATE TABLE t_audit_log (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id     BIGINT,
    operator_id BIGINT,              -- 操作者（可能是本人）
    action      VARCHAR(64),         -- READ_PROFILE / UPDATE_RECORD / ...
    resource    VARCHAR(128),        -- 被访问的资源
    ip_addr     VARCHAR(45),
    created_at  DATETIME,
    INDEX idx_user_time (user_id, created_at DESC)
);

-- 紧急事件日志（v2.0 新增：法律合规 + 家庭通知记录）
CREATE TABLE t_emergency_log (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id         BIGINT NOT NULL,
    trigger_content TEXT,            -- 触发紧急的原话（脱敏后存储）
    notified_members JSON,           -- 已通知的家庭成员
    nearby_hospitals JSON,           -- 推荐的附近医院
    created_at      DATETIME,
    INDEX idx_user (user_id)
);
```

---

## 五、数据安全与合规（v2.0 新增章节）

> 医疗场景的数据安全不是可选项，是面试时必须能回答的问题。

### 5.1 传输安全

* 全链路 HTTPS/TLS 1.3
* Java ↔ Python 内部通信走 mTLS（双向认证）
* 敏感接口（档案/报告）强制 HTTPS，Gateway 层拒绝 HTTP

### 5.2 存储安全

```java
// 敏感字段 AES-256-GCM 加密，存 VARBINARY
@Component
public class FieldEncryptor {
    // 密钥从 Vault / Nacos 配置中心读取，不硬编码
    public byte[] encrypt(String plaintext) { ... }
    public String decrypt(byte[] ciphertext) { ... }
}

// 需要加密的字段：
// t_health_profile: phone, address
// t_message: content（对话内容）
// t_report_task: result（报告解读结果）
```

### 5.3 日志脱敏

```python
# Python 侧：Logback 脱敏 Filter
import re, logging

class PiiFilter(logging.Filter):
    PATTERNS = [
        (re.compile(r'\d{11}'), '***手机号***'),        # 手机号
        (re.compile(r'\d{18}'), '***身份证***'),          # 身份证
        (re.compile(r'content="[^"]{20,}"'), 'content="[脱敏]"'),  # 对话内容
    ]

    def filter(self, record):
        msg = str(record.getMessage())
        for pattern, replacement in self.PATTERNS:
            msg = pattern.sub(replacement, msg)
        record.msg = msg
        return True
```

### 5.4 访问控制（RBAC）

```
角色定义：
- 用户本人：读写自己的数据
- 家庭成员（被授权）：只读被授权人的数据
- 平台管理员：读匿名化聚合数据，不能读个人明文数据

家庭成员数据访问：
  t_family_member 表通过 owner_id + permission_level 控制
  Gateway Filter 验证 token 中的 userId 是否有权访问目标资源
```

### 5.5 审计日志

所有数据读写操作记录到 `t_audit_log`，包括：

* 谁（userId/operatorId）在什么时候（timestamp）做了什么（action）
* 访问了哪个资源（resourceType + resourceId）
* 从哪个 IP 发起

---

## 六、跨语言通信

### 6.1 同步（HTTP · OpenFeign）

```
用户 → Gateway → Java Core → Python AI Engine
                           ├── /api/intent/classify
                           ├── /api/chat/stream（SSE）
                           └── /internal/report/analyze
```

### 6.2 异步（RocketMQ，纯 Java 内部）

```
Java → RocketMQ → Java Consumer → HTTP → Python
  report-analyze-topic
  reminder-push-topic
  diary-summary-topic
```

### 6.3 跨语言链路追踪（X-Trace-Id）

Java Gateway 生成，HTTP Header 传递，Python contextvars 接收，
SkyWalking + OpenTelemetry 双侧采集，Grafana 统一展示。

---

## 七、可观测体系

### 7.1 Prometheus 业务黄金指标（v2.0 扩充）

```python
# 技术指标（原有）
inference_latency   = Histogram("healthmate_inference_seconds", ...)
route_ratio         = Gauge("healthmate_route_ratio", ...)

# v2.0 新增业务黄金指标
safety_trigger      = Counter("healthmate_safety_trigger_total",
    "安全兜底触发次数，越多说明模型越需要迭代")

user_satisfaction   = Gauge("healthmate_user_satisfaction",
    "用户 👍/👎 比率，核心质量指标")

escalation_rate     = Gauge("healthmate_escalation_rate",
    "快速通道升级到深度通道的比率")

rag_hit_rate        = Gauge("healthmate_rag_hit_rate",
    "RAG 检索命中率，空结果比率反映知识库覆盖度")

emergency_count     = Counter("healthmate_emergency_total",
    "紧急情况触发次数，低优先级告警")
```

### 7.2 Grafana 大盘（5 个面板）

1. 系统概览：QPS、P99 延迟、错误率
2. 模型路由：四条路径比例、意图分布
3. AI 质量：MedBench 趋势、用户满意度、安全触发率
4. 资源：昇腾 NPU 利用率、显存、tokens/s
5. 合规：审计日志量、紧急事件统计

### 7.3 LangSmith AI 评估（同 v1.0）

---

## 八、14 周开发计划（v2.0 调整）

> 评审指出 11 周计划激进，特别是环境搭建和模型训练风险高。调整为 14 周，
> 微服务从 5 个精简为 3 个核心服务，博客从 8 篇精简为 5 篇核心文章。

| 周次                 | 阶段   | 主要任务                                                          | 产出                |
| -------------------- | ------ | ----------------------------------------------------------------- | ------------------- |
| **Week 0-1**   | 环境   | 昇腾环境搭建（2 周缓冲），Qwen3.5-9B 兼容性验证，意图分类数据标注 | 训练环境 + 数据就绪 |
| **Week 2**     | 模型层 | 训练意图分类器（0.5B），准确率 ≥ 95%                             | 分类器部署          |
| **Week 3-4**   | 模型层 | HealthMate-Med-9B 微调（含调参迭代），MedBench 评测               | 医疗模型 v1         |
| **Week 5**     | 模型层 | 双模型部署（vLLM-Ascend），调度器联调，报告管线验证               | 三层模型跑通        |
| **Week 6**     | 应用层 | Java 单体 + FastAPI，端到端流式对话                               | 可演示 demo         |
| **Week 7**     | 应用层 | LangGraph 状态图（含错误处理），RAG 知识库                        | 核心 AI 功能        |
| **Week 8**     | 工程层 | Java 微服务拆分（3 个），Nacos + Gateway                          | 微服务架构          |
| **Week 9**     | 工程层 | Redis ZSet（Lua 原子版），RocketMQ 管线，XXL-Job                  | 工程难点            |
| **Week 10**    | 工程层 | 分布式锁，ES 检索，Sentinel 限流，数据安全（加密/审计）           | 生产级特性          |
| **Week 11**    | 可观测 | Prometheus + Grafana + SkyWalking + LangSmith                     | 监控完成            |
| **Week 12**    | 打磨   | 文档完善，Docker Compose，在线 Demo                               | 可对外演示          |
| **Week 13-14** | 推广   | 5 篇博客发布，GitHub 推广，简历更新                               | GitHub Star++       |

### 5 篇核心博客

| 发布时间   | 标题                                                                     |
| ---------- | ------------------------------------------------------------------------ |
| Week 4 末  | 《在昇腾 910B 上微调 Qwen3.5-9B 医疗大模型：从数据准备到 MedBench 评测》 |
| Week 5 末  | 《双模型路由架构：用 0.5B 意图分类器驱动千毫秒级 LLM 调度》              |
| Week 7 末  | 《医疗 RAG 的 5 个工程陷阱：从 chunk 策略到多阶段报告管线》              |
| Week 9 末  | 《Redis ZSet + Lua 原子操作：百万级健康提醒的并发安全实践》              |
| Week 12 末 | 《14 周从零到 HealthMate：对标蚂蚁阿福的完整技术复盘》                   |

---

## 九、简历终版（v2.0 更新）

```
HealthMate · 自训医疗大模型驱动的全栈 AI 健康助手（开源）
个人项目 · 2026.xx - 2026.xx · GitHub xxx star · 对标蚂蚁阿福

技术栈：
[模型层]  昇腾 910B · LLaMA-Factory · Qwen3.5-9B LoRA · Qwen3.6-35B-A3B · MedBench
[AI 层]   FastAPI · LangChain · LangGraph · BGE-M3 · Milvus · LangSmith
[工程层]  Spring Boot 3 · Spring Cloud · Redis · RocketMQ · Elasticsearch · XXL-Job
[安全]    AES-256-GCM 字段加密 · PII 脱敏 · RBAC · 审计日志
[基础设施] Docker · Prometheus · Grafana · SkyWalking · Nacos · Sentinel

核心成果：

▌模型层
• 基于昇腾 910B 集群 LoRA 微调 Qwen3.5-9B 医疗垂类大模型 HealthMate-Med-9B。
  4000 条精标数据（问诊/报告/用药/安全兜底）。
  MedBench CMB-Clin 相比基座提升 X%。

▌模型调度（核心亮点）
• 三层智能调度：0.5B 意图分类器（Top-2 输出，7 类 96% 准确率）→ FastAPI
  调度层（四条路径 + 熔断降级）→ 双模型执行（35B-A3B 快速 + 9B 深度）。
  推理成本比全程用 14B 降低 60%，P99 延迟从 8s 降到 3s。
  独立报告管线（35B 视觉提取 → RAG → 9B 生成）解决多模态+专业解读的矛盾。
  灰度发布机制（按 user_id hash 分流）支持模型版本 A/B 测试。

▌AI 应用层
• LangGraph 状态图编排四条路径，含降级节点和安全拦截节点。
• 混合检索（BM25+向量+BGE-M3 Reranker）准确率较单一检索提升 25%。
• 结构化上下文压缩策略（保留关键轮次 + 提取症状/用药/否认项），保障医疗安全。

▌工程层（覆盖昨天面试被问的全部问题）
• 3 个 Java 微服务 + 1 个 Python 服务，Spring Cloud 全家桶。
• Redis ZSet + Lua 原子脚本实现百万级健康提醒优先级队列（并发安全）。
• Redisson 分布式锁（健康档案并发写 + AI 配额扣减，含看门狗续期）。
• RocketMQ 异步报告解读管线（Java Consumer → HTTP 转发 → Python AI）。
• XXL-Job 分布式定时（按 user_id 分片调度提醒推送）。
• Elasticsearch 医学知识检索 + 用户行为聚合。
• Sentinel 用户级限流 + 全局限流。

▌数据安全
• AES-256-GCM 加密存储敏感字段（对话内容/报告结果/手机号）。
• 全链路日志 PII 脱敏（手机号/身份证/对话内容自动过滤）。
• 完整审计日志（t_audit_log，记录所有数据访问行为）。
• RBAC 访问控制（本人/家庭成员/管理员三级权限）。

▌可观测
• Prometheus + Grafana（技术指标 + 业务黄金指标：安全触发率/用户满意度/RAG 命中率）。
• SkyWalking 跨语言链路追踪。
• LangSmith 100 条评估集自动化 AI 质量监控。

▌产出
• 在线 Demo · 演示视频 · 5 篇技术博客 · 完整文档
```

---

## 十、面试讲故事脚本（v2.0 补充）

### 原有脚本（见 v1.0，保持不变）

### v2.0 新增：被追问架构细节

**"报告解读为什么不直接用 35B-A3B 生成解读？"**

> "35B-A3B 做视觉理解很强，能提取图片里的异常项目，但它没有经过医疗 SFT，
> 生成的解读专业度不够。所以我设计了独立的报告管线：35B-A3B 负责'看懂图片'，
> 提取结构化的异常发现，然后结合 RAG 检索的医学文献，交给自训的 9B 医疗模型
> 生成专业解读。两个模型各干自己最擅长的。"

**"ZSet 提醒队列怎么防止重复消费？"**

> "v1 的时候用 rangeByScore + remove，但两步操作不原子，多实例部署会竞态。
> 我改成 Lua 脚本，在 Redis 单线程执行层面保证'取出并立刻删除'是原子操作。
> 这是我做压测时发现的 bug，修复过程本身也是一个面试素材。"

**"医疗数据安全怎么保证？"**

> "三个层面：存储层对话内容和报告结果用 AES-256-GCM 加密，密钥走配置中心
> 不硬编码；传输层全链路 HTTPS；访问层有审计日志，记录所有数据读写行为，
> 合规检查时能追溯。日志系统加了 PII 脱敏过滤器，手机号身份证不会出现在日志里。"

**"模型迭代时怎么保证线上稳定？"**

> "我做了灰度发布机制——新模型不直接替换，按 user_id hash 做稳定分流，
> 先给 10% 用户用新版，用 LangSmith 对比两个版本的准确率和安全触发率，
> 数据好了再全量切换，48 小时内保留旧版可以随时回滚。"

---

## 十一、待确认项

* [ ] Qwen3.5-9B 在昇腾 910B4 上的兼容性（Week 0 验证）
* [ ] HealthMate-Med-9B MedBench CMB-Exam 准确率：____%
* [ ] 相比基座提升：____%
* [ ] 双模型路由 P99 延迟：____ms
* [ ] 快速/深度通道路由比例：____% / ____%
* [ ] GitHub star 数：____
* [ ] 在线 Demo URL：____

---

## 十二、评审变更记录

| 版本 | 日期    | 变更内容                                                                                                                                                                                                                                                                          |
| ---- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| v1.0 | 2026-05 | 初始版本                                                                                                                                                                                                                                                                          |
| v2.0 | 2026-05 | 修复报告解读路由矛盾（独立管线）；ZSet 竞态条件改 Lua 原子；新增数据安全章节；RocketMQ Python 侧改 HTTP 转发；混合意图 Top-2 输出；LangGraph 加错误处理节点；上下文压缩改结构化提取；加灰度发布机制；业务黄金指标；急救增强；微服务精简为 3 个；计划调整为 14 周；博客精简为 5 篇 |
