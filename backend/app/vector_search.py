"""
向量语义搜索 - 基于 sentence-transformers + numpy
使用中文语义模型为标准名称生成向量，支持语义相似度搜索
"""

import os
import json
import logging
import threading
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

VECTORS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vectors")
EMBEDDINGS_PATH = os.path.join(VECTORS_DIR, "embeddings.npy")
IDS_PATH = os.path.join(VECTORS_DIR, "ids.json")
META_PATH = os.path.join(VECTORS_DIR, "meta.json")

# BGE 中文语义模型，中文检索效果优于多语言模型（约 400MB）
MODEL_NAME = "BAAI/bge-base-zh-v1.5"

_model = None
_model_lock = threading.Lock()
_embeddings = None
_ids = None

# 索引构建状态
index_state = {
    "is_building": False,
    "message": "",
}


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                logger.info(f"正在加载语义模型 {MODEL_NAME}...")
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer(MODEL_NAME)
                logger.info("语义模型加载完成")
    return _model


def _load_index():
    """加载已有的向量索引"""
    global _embeddings, _ids
    if os.path.exists(EMBEDDINGS_PATH) and os.path.exists(IDS_PATH):
        try:
            _embeddings = np.load(EMBEDDINGS_PATH)
            with open(IDS_PATH, "r") as f:
                _ids = json.load(f)
            logger.info(f"向量索引已加载: {len(_ids)} 条")
            return True
        except Exception as e:
            logger.error(f"加载向量索引失败: {e}")
    return False


def build_index(db_session):
    """为所有标准构建向量索引"""
    from .models import Standard

    index_state["is_building"] = True
    index_state["message"] = "正在构建向量索引..."

    try:
        standards = db_session.query(Standard).all()
        if not standards:
            index_state["message"] = "数据库中没有标准数据"
            return

        # 构建文本: 标准号 + 中文名称 + 类型
        texts = []
        ids = []
        for s in standards:
            text = f"{s.standard_number} {s.cn_name}"
            if s.standard_type:
                text += f" {s.standard_type}"
            if s.category:
                text += f" {s.category}"
            texts.append(text)
            ids.append(s.id)

        index_state["message"] = f"正在为 {len(texts)} 条标准生成语义向量..."
        logger.info(f"开始生成向量: {len(texts)} 条标准")

        model = _get_model()
        embeddings = model.encode(texts, batch_size=64, show_progress_bar=False,
                                  normalize_embeddings=True)

        os.makedirs(VECTORS_DIR, exist_ok=True)
        np.save(EMBEDDINGS_PATH, embeddings)
        with open(IDS_PATH, "w") as f:
            json.dump(ids, f)
        with open(META_PATH, "w") as f:
            json.dump({
                "count": len(ids),
                "model": MODEL_NAME,
                "built_at": datetime.now().isoformat(),
            }, f)

        global _embeddings, _ids
        _embeddings = embeddings
        _ids = ids

        index_state["message"] = f"向量索引构建完成: {len(ids)} 条"
        logger.info(f"向量索引构建完成: {len(ids)} 条")

    except Exception as e:
        index_state["message"] = f"构建失败: {str(e)}"
        logger.error(f"构建向量索引失败: {e}", exc_info=True)
    finally:
        index_state["is_building"] = False


def search(query: str, top_k: int = 50) -> list[tuple[int, float]]:
    """语义搜索，返回 [(standard_id, score), ...]"""
    global _embeddings, _ids

    if _embeddings is None or _ids is None:
        if not _load_index():
            return []

    try:
        model = _get_model()
        # BGE 模型查询时需加指令前缀以提升检索效果
        query_text = f"为这个句子生成表示以用于检索相关段落：{query}"
        query_vec = model.encode([query_text], normalize_embeddings=True)
        scores = np.dot(_embeddings, query_vec.T).flatten()
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(int(_ids[i]), float(scores[i])) for i in top_indices if scores[i] > 0.1]
    except Exception as e:
        logger.error(f"语义搜索失败: {e}")
        return []


def get_index_status() -> dict:
    if os.path.exists(META_PATH):
        try:
            with open(META_PATH, "r") as f:
                meta = json.load(f)
            return {
                "exists": True,
                "count": meta.get("count", 0),
                "model": meta.get("model", ""),
                "built_at": meta.get("built_at", ""),
                "is_building": index_state["is_building"],
                "message": index_state["message"],
            }
        except Exception:
            pass
    return {
        "exists": False,
        "count": 0,
        "model": MODEL_NAME,
        "built_at": "",
        "is_building": index_state["is_building"],
        "message": index_state["message"],
    }
