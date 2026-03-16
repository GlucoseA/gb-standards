"""
AI API 配置管理 - 读写 ai_config.json
支持 LLM (chat) 和 Embedding 两套独立配置
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

_default_dir = os.path.dirname(os.path.dirname(__file__))
_data_dir = os.getenv("DATA_DIR", _default_dir)
CONFIG_PATH = os.path.join(_data_dir, "ai_config.json")

DEFAULT_CONFIG = {
    "api_url": "https://api.deepseek.com/chat/completions",
    "api_key": "",
    "model": "deepseek-chat",
}

DEFAULT_EMBEDDING_CONFIG = {
    "embedding_url": "https://open.bigmodel.cn/api/paas/v4/embeddings",
    "embedding_key": "",
    "embedding_model": "embedding-3",
}


def load_config() -> dict:
    # 环境变量优先（适用于生产环境）
    env_key = os.getenv("AI_API_KEY")
    if env_key:
        return {
            "api_url": os.getenv("AI_API_URL", DEFAULT_CONFIG["api_url"]),
            "api_key": env_key,
            "model": os.getenv("AI_MODEL", DEFAULT_CONFIG["model"]),
        }
    # 回退到配置文件（适用于开发环境）
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                cfg.setdefault(k, v)
            return cfg
        except Exception as e:
            logger.error(f"读取配置失败: {e}")
    return dict(DEFAULT_CONFIG)


def load_embedding_config() -> dict:
    """加载 Embedding API 配置：环境变量 → 配置文件 → 默认值"""
    env_key = os.getenv("EMBEDDING_API_KEY")
    if env_key:
        return {
            "embedding_url": os.getenv("EMBEDDING_API_URL", DEFAULT_EMBEDDING_CONFIG["embedding_url"]),
            "embedding_key": env_key,
            "embedding_model": os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_CONFIG["embedding_model"]),
        }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return {
                "embedding_url": cfg.get("embedding_url", DEFAULT_EMBEDDING_CONFIG["embedding_url"]),
                "embedding_key": cfg.get("embedding_key", DEFAULT_EMBEDDING_CONFIG["embedding_key"]),
                "embedding_model": cfg.get("embedding_model", DEFAULT_EMBEDDING_CONFIG["embedding_model"]),
            }
        except Exception as e:
            logger.error(f"读取 Embedding 配置失败: {e}")
    return dict(DEFAULT_EMBEDDING_CONFIG)


def save_config(config: dict):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存配置失败: {e}")
        raise


def mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return "***"
    return key[:3] + "*" * (len(key) - 7) + key[-4:]
