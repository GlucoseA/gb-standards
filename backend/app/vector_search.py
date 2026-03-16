"""
向量语义搜索 - 基于智谱 (Zhipu) Embedding API + numpy
调用云端 Embedding API 生成向量，支持语义相似度搜索
"""

import os
import json
import logging
import threading
import numpy as np
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

_default_dir = os.path.dirname(os.path.dirname(__file__))
_data_dir = os.getenv("DATA_DIR", _default_dir)
VECTORS_DIR = os.path.join(_data_dir, "vectors")
EMBEDDINGS_PATH = os.path.join(VECTORS_DIR, "embeddings.npy")
IDS_PATH = os.path.join(VECTORS_DIR, "ids.json")
META_PATH = os.path.join(VECTORS_DIR, "meta.json")

# 默认使用智谱 embedding-3
DEFAULT_EMBEDDING_URL = "https://open.bigmodel.cn/api/paas/v4/embeddings"
DEFAULT_EMBEDDING_MODEL = "embedding-3"

_embeddings = None
_ids = None

# 索引构建状态
index_state = {
    "is_building": False,
    "message": "",
}


def _get_embedding_config() -> dict:
    """获取 Embedding API 配置，优先环境变量，其次配置文件"""
    from .config_manager import load_embedding_config
    return load_embedding_config()


def _call_embedding_api(texts: list[str], config: dict) -> np.ndarray:
    """调用 Embedding API，返回归一化后的向量矩阵

    智谱 API 支持批量输入，但有长度限制，这里分批处理。
    """
    api_url = config.get("embedding_url") or DEFAULT_EMBEDDING_URL
    api_key = config.get("embedding_key") or ""
    model = config.get("embedding_model") or DEFAULT_EMBEDDING_MODEL

    if not api_key:
        raise ValueError("未配置 Embedding API Key，请在 AI 配置页面或环境变量中设置")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    all_embeddings = []
    batch_size = 64  # 智谱 API 单次上限 64 条
    max_retries = 3

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        payload = {
            "model": model,
            "input": batch,
        }

        # 带重试的请求
        for attempt in range(max_retries):
            try:
                resp = requests.post(api_url, headers=headers, json=payload, timeout=60)
                resp.raise_for_status()
                result = resp.json()
                break
            except (requests.RequestException, ValueError) as e:
                if attempt < max_retries - 1:
                    import time
                    wait = 2 ** attempt
                    logger.warning(f"Embedding 请求失败 (尝试 {attempt + 1}/{max_retries}): {e}, {wait}s 后重试")
                    time.sleep(wait)
                else:
                    raise

        # 兼容 OpenAI 格式的响应
        data = result.get("data", [])
        if not data:
            raise ValueError(f"Embedding API 返回为空: {result}")

        # 按 index 排序确保顺序正确
        data.sort(key=lambda x: x.get("index", 0))
        batch_vecs = [item["embedding"] for item in data]
        all_embeddings.extend(batch_vecs)

        if i + batch_size < len(texts):
            logger.info(f"Embedding 进度: {min(i + batch_size, len(texts))}/{len(texts)}")

    matrix = np.array(all_embeddings, dtype=np.float32)
    # L2 归一化
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    matrix = matrix / norms
    return matrix


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


def _standard_to_text(s) -> str:
    """将标准记录转换为用于 embedding 的文本"""
    text = f"{s.standard_number} {s.cn_name}"
    if s.standard_type:
        text += f" {s.standard_type}"
    if s.category:
        text += f" {s.category}"
    return text


def _save_index(ids: list, embeddings: np.ndarray, config: dict):
    """保存向量索引到磁盘并更新内存"""
    global _embeddings, _ids

    os.makedirs(VECTORS_DIR, exist_ok=True)
    np.save(EMBEDDINGS_PATH, embeddings)
    with open(IDS_PATH, "w") as f:
        json.dump(ids, f)
    with open(META_PATH, "w") as f:
        json.dump({
            "count": len(ids),
            "model": config.get("embedding_model") or DEFAULT_EMBEDDING_MODEL,
            "api_url": config.get("embedding_url") or DEFAULT_EMBEDDING_URL,
            "dimension": int(embeddings.shape[1]),
            "built_at": datetime.now().isoformat(),
        }, f)

    _embeddings = embeddings
    _ids = ids


def build_index(db_session, force_full=False):
    """构建向量索引（增量或全量）

    - 如果已有索引且 force_full=False，只为新增标准生成向量（增量）
    - 如果没有索引或 force_full=True，为全部标准生成向量（全量）
    - 已被删除的标准（DB 中不存在但索引中存在）会被自动清理
    """
    from .models import Standard

    index_state["is_building"] = True
    index_state["message"] = "正在构建向量索引..."

    try:
        config = _get_embedding_config()
        if not config.get("embedding_key"):
            index_state["message"] = "未配置 Embedding API Key，无法构建索引"
            logger.warning("未配置 Embedding API Key，跳过向量索引构建")
            return

        standards = db_session.query(Standard).all()
        if not standards:
            index_state["message"] = "数据库中没有标准数据"
            return

        db_ids = {s.id for s in standards}
        db_map = {s.id: s for s in standards}

        # 尝试加载已有索引
        existing_ids = []
        existing_embeddings = None
        if not force_full and os.path.exists(EMBEDDINGS_PATH) and os.path.exists(IDS_PATH):
            try:
                existing_embeddings = np.load(EMBEDDINGS_PATH)
                with open(IDS_PATH, "r") as f:
                    existing_ids = json.load(f)
                logger.info(f"已有索引: {len(existing_ids)} 条")
            except Exception as e:
                logger.warning(f"加载已有索引失败，将执行全量构建: {e}")
                existing_ids = []
                existing_embeddings = None

        existing_id_set = set(existing_ids)

        # 找出新增的标准（DB 中有但索引中没有）
        new_ids = [sid for sid in db_ids if sid not in existing_id_set]
        # 找出需要删除的（索引中有但 DB 中已不存在）
        removed_ids = [sid for sid in existing_ids if sid not in db_ids]

        # 如果没有已有索引，执行全量构建
        if existing_embeddings is None or len(existing_ids) == 0:
            logger.info("无已有索引，执行全量构建")
            texts = [_standard_to_text(db_map[sid]) for sid in sorted(db_ids)]
            all_ids = sorted(db_ids)

            index_state["message"] = f"全量构建: 正在为 {len(texts)} 条标准调用 Embedding API..."
            logger.info(f"全量构建: {len(texts)} 条标准")

            embeddings = _call_embedding_api(texts, config)
            _save_index(all_ids, embeddings, config)

            index_state["message"] = f"向量索引全量构建完成: {len(all_ids)} 条"
            logger.info(f"向量索引全量构建完成: {len(all_ids)} 条, 维度: {embeddings.shape[1]}")
            return

        # 无变化
        if not new_ids and not removed_ids:
            index_state["message"] = f"向量索引已是最新: {len(existing_ids)} 条，无需更新"
            logger.info("向量索引已是最新，无需更新")
            # 确保内存中有索引
            if _embeddings is None:
                _load_index()
            return

        logger.info(f"增量更新: 新增 {len(new_ids)} 条, 删除 {len(removed_ids)} 条")

        # 第一步：清理已删除的标准
        if removed_ids:
            removed_set = set(removed_ids)
            keep_mask = [i for i, sid in enumerate(existing_ids) if sid not in removed_set]
            existing_embeddings = existing_embeddings[keep_mask]
            existing_ids = [existing_ids[i] for i in keep_mask]
            logger.info(f"已清理 {len(removed_ids)} 条已删除标准的向量")

        # 第二步：为新增标准生成向量
        if new_ids:
            new_ids_sorted = sorted(new_ids)
            new_texts = [_standard_to_text(db_map[sid]) for sid in new_ids_sorted]

            index_state["message"] = f"增量更新: 正在为 {len(new_texts)} 条新标准调用 Embedding API..."
            logger.info(f"增量更新: 为 {len(new_texts)} 条新标准生成向量")

            new_embeddings = _call_embedding_api(new_texts, config)

            # 合并
            final_ids = existing_ids + new_ids_sorted
            final_embeddings = np.concatenate([existing_embeddings, new_embeddings], axis=0)
        else:
            final_ids = existing_ids
            final_embeddings = existing_embeddings

        _save_index(final_ids, final_embeddings, config)

        index_state["message"] = f"向量索引增量更新完成: 总 {len(final_ids)} 条 (新增 {len(new_ids)}, 删除 {len(removed_ids)})"
        logger.info(f"向量索引增量更新完成: 总 {len(final_ids)} 条 (新增 {len(new_ids)}, 删除 {len(removed_ids)})")

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
        config = _get_embedding_config()
        if not config.get("embedding_key"):
            logger.warning("未配置 Embedding API Key，无法进行语义搜索")
            return []

        query_vec = _call_embedding_api([query], config)
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
                "api_url": meta.get("api_url", ""),
                "dimension": meta.get("dimension", 0),
                "built_at": meta.get("built_at", ""),
                "is_building": index_state["is_building"],
                "message": index_state["message"],
            }
        except Exception:
            pass
    return {
        "exists": False,
        "count": 0,
        "model": DEFAULT_EMBEDDING_MODEL,
        "api_url": DEFAULT_EMBEDDING_URL,
        "dimension": 0,
        "built_at": "",
        "is_building": index_state["is_building"],
        "message": index_state["message"],
    }
