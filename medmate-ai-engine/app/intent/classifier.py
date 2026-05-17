"""
意图分类器 - Qwen2.5-0.5B LoRA 微调模型
训练数据：800-1000 条，7 类，ShareGPT 格式
评估目标：准确率 ≥ 95%
"""
from app.intent.schemas import IntentResult, INTENT_LABELS
from app.config import settings


class IntentClassifier:
    """
    意图分类器
    - 基座：Qwen2.5-0.5B-Instruct
    - 微调：LoRA（训练后加载）
    - 输出：Top-2 意图 + 置信度
    - 延迟目标：< 50ms
    """

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.is_loaded = False

    def load(self):
        """加载模型（应用启动时调用）"""
        # TODO: Week 2 实现
        # 1. 加载 Qwen2.5-0.5B-Instruct 基座
        # 2. 如果有 LoRA 权重，合并加载
        # from transformers import AutoModelForCausalLM, AutoTokenizer
        # from peft import PeftModel
        # self.tokenizer = AutoTokenizer.from_pretrained(settings.intent_model_path)
        # self.model = AutoModelForCausalLM.from_pretrained(settings.intent_model_path)
        # if settings.intent_lora_path:
        #     self.model = PeftModel.from_pretrained(self.model, settings.intent_lora_path)
        self.is_loaded = True
        print("[OK] Intent classifier loaded")

    def classify(self, text: str) -> IntentResult:
        """
        对用户输入进行意图分类

        Args:
            text: 用户输入文本

        Returns:
            IntentResult: Top-2 意图 + 置信度
        """
        # TODO: Week 2 实现真实推理
        # 骨架阶段返回默认值
        return IntentResult(
            primary_intent="health_qa",
            primary_confidence=0.92,
            secondary_intent=None,
            secondary_confidence=0.0,
        )

    def unload(self):
        """释放模型资源"""
        self.model = None
        self.tokenizer = None
        self.is_loaded = False


# 全局单例
intent_classifier = IntentClassifier()
