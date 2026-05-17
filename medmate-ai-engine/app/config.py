"""
HealthMate AI Engine - 配置管理
使用 Pydantic Settings，支持 .env 文件和环境变量
切换 AI_PROVIDER 即可在 dashscope / ollama 之间切换
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """全局配置"""

    # --- 服务配置 ---
    app_name: str = "HealthMate AI Engine"
    app_port: int = 8090
    debug: bool = False

    # --- AI Provider 切换（dashscope / ollama） ---
    ai_provider: str = "dashscope"  # 当前用百炼，微调好后改为 "ollama"

    # --- 阿里云百炼 DashScope（OpenAI 兼容接口） ---
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_fast_model: str = "qwen3.6-flash"       # 快速通道
    dashscope_med_model: str = "qwen3.6-flash"          # 深度通道（开发阶段统一用 flash）

    # --- Ollama（本地微调模型） ---
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_fast_model: str = "qwen2.5:7b"
    ollama_med_model: str = "healthmate-med"

    # --- 当前生效的模型配置（根据 ai_provider 自动选择） ---
    @property
    def active_base_url(self) -> str:
        if self.ai_provider == "dashscope":
            return self.dashscope_base_url
        return self.ollama_base_url

    @property
    def active_api_key(self) -> str:
        if self.ai_provider == "dashscope":
            return self.dashscope_api_key
        return "ollama"

    @property
    def active_fast_model(self) -> str:
        if self.ai_provider == "dashscope":
            return self.dashscope_fast_model
        return self.ollama_fast_model

    @property
    def active_med_model(self) -> str:
        if self.ai_provider == "dashscope":
            return self.dashscope_med_model
        return self.ollama_med_model

    # --- 模型路径（本地微调用） ---
    intent_model_path: str = "D:/models/Qwen2.5-0.5B-Instruct"
    intent_lora_path: str = ""  # empty = use keyword classifier; set path to use LoRA model
    medical_model_path: str = "D:/models/Qwen2.5-7B"
    medical_lora_path: str = ""
    embedding_model_path: str = "C:/Users/13203/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181"

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- MySQL ---
    mysql_url: str = "mysql+pymysql://root:12050516@localhost:3306/healthmate"

    # --- Milvus ---
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection: str = "medical_kb"

    # --- Elasticsearch ---
    es_url: str = "http://localhost:9200"
    es_index: str = "medical_kb"

    # --- Java Core 回调 ---
    java_core_url: str = "http://localhost:8081"

    # --- 安全 ---
    aes_key: str = ""

    # --- 监控 ---
    enable_metrics: bool = True
    langsmith_api_key: str = ""

    class Config:
        env_file = ".env"
        env_prefix = "HM_"
        extra = "ignore"  # 忽略 .env 中非 HM_ 前缀的变量


settings = Settings()
