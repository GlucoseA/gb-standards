"""
调用 LLM API 对国家标准进行通俗化总结
支持任意 OpenAI 兼容接口（DeepSeek、OpenAI、Ollama 等）
"""

import requests
import logging

from .config_manager import load_config

logger = logging.getLogger(__name__)


def summarize_standard(standard_number: str, cn_name: str, status: str,
                       implement_date: str = "", abolish_date: str = "",
                       replaced_by: str = "", ics_code: str = "",
                       ccs_code: str = "", client_config: dict = None) -> str:
    info_parts = [
        f"标准号: {standard_number}",
        f"标准名称: {cn_name}",
        f"状态: {status}",
    ]
    if implement_date:
        info_parts.append(f"实施日期: {implement_date}")
    if abolish_date:
        info_parts.append(f"废止日期: {abolish_date}")
    if replaced_by:
        info_parts.append(f"替代标准: {replaced_by}")
    if ics_code:
        info_parts.append(f"ICS分类: {ics_code}")
    if ccs_code:
        info_parts.append(f"CCS分类: {ccs_code}")

    standard_info = "\n".join(info_parts)

    prompt = f"""基于以下国家标准信息，生成一段专业简明的解读（100字以内）。要求：说明标准适用范围、核心规范内容、当前效力状态。直接输出，无需标题。

{standard_info}"""

    return _call_llm(prompt, client_config)


def summarize_standard_rich(standard_number: str, cn_name: str, status: str,
                            raw_fields: dict = None, client_config: dict = None) -> str:
    info_parts = [
        f"标准号: {standard_number}",
        f"标准名称: {cn_name}",
        f"状态: {status}",
    ]

    if raw_fields:
        for key, value in raw_fields.items():
            if value and key not in ("标准名称",):
                info_parts.append(f"{key}: {value}")

    standard_info = "\n".join(info_parts)

    prompt = f"""基于以下国家标准详细信息，生成专业简明的解读（150字以内）。要求：说明适用范围与核心规范内容、当前效力状态、归口管理部门（如有）。直接输出，无需标题。

{standard_info}"""

    return _call_llm(prompt, client_config)


def test_connection(client_config: dict = None) -> dict:
    """测试 AI 连接是否可用"""
    config = _resolve_config(client_config)
    api_url = config.get("api_url", "")
    api_key = config.get("api_key", "")
    model = config.get("model", "")

    if not api_url or not api_key:
        return {"success": False, "message": "未配置 API 地址或密钥"}

    try:
        resp = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 10,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return {"success": True, "message": f"连接成功，模型: {model}"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}


def _resolve_config(client_config: dict = None) -> dict:
    """优先使用客户端提供的配置，否则回退到服务端配置"""
    if client_config and client_config.get("api_key"):
        server_cfg = load_config()
        return {
            "api_url": client_config.get("api_url") or server_cfg.get("api_url", ""),
            "api_key": client_config["api_key"],
            "model": client_config.get("model") or server_cfg.get("model", ""),
        }
    return load_config()


def _call_llm(prompt: str, client_config: dict = None) -> str:
    config = _resolve_config(client_config)
    api_url = config.get("api_url", "")
    api_key = config.get("api_key", "")
    model = config.get("model", "")

    if not api_url or not api_key:
        return "请先在 LLM API 设定中配置接口地址和密钥"

    try:
        resp = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 400,
                "temperature": 0.7,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"LLM API 调用失败: {e}")
        return f"AI 摘要生成失败: {str(e)}"
