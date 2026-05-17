"""
意图分类训练数据生成器
用 DashScope qwen3.6-flash 批量生成，ShareGPT 格式供 LLaMA-Factory 训练
"""
import json
import os
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("HM_DASHSCOPE_API_KEY"),
)

# 7 类意图 + 每类的生成提示
INTENT_CONFIG = {
    "casual_chat": {
        "count": 100,
        "prompt": """请生成{count}条中文日常闲聊的句子，这些句子是用户对一个健康助手说的，但不涉及任何健康问题。
要求：
- 包含打招呼、聊天气、聊心情、开玩笑、感谢、告别等场景
- 语气自然口语化，长短不一（3-30字）
- 不要编号，每行一条
- 不要重复""",
    },
    "health_qa": {
        "count": 200,
        "prompt": """请生成{count}条中文健康知识问答的句子，这些是用户向健康助手提出的健康科普类问题。
要求：
- 涵盖：营养饮食、运动健身、睡眠、体检指标含义、常见病预防、中医养生等
- 是提问形式，不是描述症状
- 语气自然口语化，长短不一
- 不要编号，每行一条
- 不要重复""",
    },
    "symptom_consult": {
        "count": 200,
        "prompt": """请生成{count}条中文症状咨询的句子，这些是用户向健康助手描述自己身体不适的话。
要求：
- 涵盖：头疼、胃疼、发烧、咳嗽、失眠、皮肤问题、关节疼、心悸、眩晕等各类症状
- 有的描述单一症状，有的描述多种症状组合
- 有的包含持续时间（"已经三天了"）、程度（"很严重"）、触发条件（"吃完饭就疼"）
- 语气自然口语化，像真实患者说的话
- 不要编号，每行一条""",
    },
    "drug_consult": {
        "count": 150,
        "prompt": """请生成{count}条中文用药咨询的句子，这些是用户向健康助手询问药物相关问题。
要求：
- 涵盖：药物用法用量、副作用、药物相互作用、能否一起吃、孕妇/儿童用药、中成药等
- 提到具体药名（布洛芬、阿莫西林、头孢、降压药、二甲双胍、感冒灵等）
- 语气自然口语化
- 不要编号，每行一条""",
    },
    "report_parse": {
        "count": 120,
        "prompt": """请生成{count}条中文体检报告解读请求的句子，这些是用户请健康助手帮忙看报告或解读指标。
要求：
- 涵盖：血常规、肝功能、肾功能、血糖、血脂、尿常规、心电图、B超、CT等
- 有的给出具体数值（"转氨酶85"、"血糖7.2"、"甘油三酯2.8"）
- 有的请求看图片/报告（"帮我看看这个报告"、"这个检查结果正常吗"）
- 语气自然口语化
- 不要编号，每行一条""",
    },
    "emergency": {
        "count": 80,
        "prompt": """请生成{count}条中文紧急健康情况的句子，这些是用户在紧急情况下向健康助手求助的话。
要求：
- 涵盖：胸痛胸闷、呼吸困难、大量出血、严重过敏、意识模糊、中毒、高热不退、心理危机（不想活了/想自残）等
- 语气紧张急迫，像真实紧急情况
- 注意：心理危机类的要包含（但生成时注意这是训练数据用途）
- 不要编号，每行一条""",
    },
    "task_command": {
        "count": 100,
        "prompt": """请生成{count}条中文任务指令的句子，这些是用户请健康助手执行具体操作的话。
要求：
- 涵盖：设置提醒（吃药/喝水/运动/复查）、记录数据（血压/血糖/体重/心率）、查询历史记录、管理健康档案
- 包含具体时间（"明天早上8点"、"每天下午3点"）和具体数值（"血压130/85"、"体重72公斤"）
- 语气自然，像在指挥助手干活
- 不要编号，每行一条""",
    },
}

# 系统提示词模板（分类器训练用）
CLASSIFIER_SYSTEM = "你是一个医疗意图分类器。请将用户的输入分类为以下7个类别之一：casual_chat(日常闲聊), health_qa(健康知识问答), symptom_consult(症状咨询), drug_consult(用药咨询), report_parse(报告解读), emergency(紧急情况), task_command(任务指令)。只输出类别标签，不要解释。"


def generate_examples(intent: str, config: dict) -> list[str]:
    """用 LLM 批量生成某类意图的示例句子"""
    count = config["count"]
    prompt = config["prompt"].format(count=count)

    print(f"[GEN] Generating {count} examples for '{intent}'...", flush=True)

    response = client.chat.completions.create(
        model="qwen3.6-flash",
        messages=[
            {"role": "system", "content": "你是一个数据生成助手，请严格按要求生成训练数据。不要输出任何多余内容。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.9,
        max_tokens=8000,
        timeout=120,
        extra_body={"enable_thinking": False},  # 关闭思考模式，加速生成
    )

    text = response.choices[0].message.content
    # 按行分割，过滤空行和编号
    lines = []
    for line in text.strip().split("\n"):
        line = line.strip()
        # 去掉可能的编号前缀（1. 2. 等）
        if line and len(line) > 1:
            import re
            line = re.sub(r"^\d+[\.\、\)\]]\s*", "", line)
            line = line.strip("- ").strip()
            if line and len(line) >= 2:
                lines.append(line)

    print(f"  -> Got {len(lines)} examples")
    return lines


def build_sharegpt_data(all_data: dict) -> list[dict]:
    """构建 ShareGPT 格式数据"""
    dataset = []
    for intent, examples in all_data.items():
        for example in examples:
            dataset.append({
                "conversations": [
                    {
                        "from": "system",
                        "value": CLASSIFIER_SYSTEM,
                    },
                    {
                        "from": "human",
                        "value": example,
                    },
                    {
                        "from": "gpt",
                        "value": intent,
                    },
                ]
            })
    return dataset


def main():
    all_data = {}
    total = 0

    for intent, config in INTENT_CONFIG.items():
        examples = generate_examples(intent, config)
        all_data[intent] = examples
        total += len(examples)
        time.sleep(1)  # 避免限频

    # 构建 ShareGPT 格式
    dataset = build_sharegpt_data(all_data)

    # 打乱顺序
    import random
    random.shuffle(dataset)

    # 分割：90% 训练，10% 验证
    split = int(len(dataset) * 0.9)
    train_data = dataset[:split]
    val_data = dataset[split:]

    # 保存
    os.makedirs("training/data", exist_ok=True)

    with open("training/data/intent_train.json", "w", encoding="utf-8") as f:
        json.dump(train_data, f, ensure_ascii=False, indent=2)

    with open("training/data/intent_val.json", "w", encoding="utf-8") as f:
        json.dump(val_data, f, ensure_ascii=False, indent=2)

    # 统计
    print(f"\n{'='*50}")
    print(f"Total: {total} examples")
    print(f"Train: {len(train_data)} | Val: {len(val_data)}")
    print(f"\nPer intent:")
    for intent, examples in all_data.items():
        print(f"  {intent}: {len(examples)}")
    print(f"\nSaved to training/data/intent_train.json")
    print(f"Saved to training/data/intent_val.json")


if __name__ == "__main__":
    main()
