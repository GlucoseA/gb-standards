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
                       ccs_code: str = "") -> str:
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

    prompt = f"""你是一个国家标准解读专家。请根据以下国家标准信息，用通俗易懂的语言为普通消费者生成一段简明摘要（150字以内），重点说明：
1. 这个标准是关于什么的（涉及哪类商品/产品）
2. 对消费者购物有什么参考价值
3. 当前状态（是否生效、是否即将废止等）

标准信息：
{standard_info}

请直接输出摘要，不要加标题或前缀。"""

    return _call_llm(prompt)


def summarize_standard_rich(standard_number: str, cn_name: str, status: str,
                            raw_fields: dict = None) -> str:
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

    prompt = f"""你是一个国家标准解读专家。请根据以下从国家标准委官网爬取的标准详细信息，用通俗易懂的语言为普通消费者生成一段摘要（200字以内），重点说明：
1. 这个标准具体规范了什么（涉及哪类商品/产品/行业）
2. 对普通消费者购物或日常生活有什么实际参考价值
3. 当前状态说明（是否已生效、即将实施、或已废止）
4. 如果有归口部门或主管部门，简要说明由谁负责监管

标准完整信息：
{standard_info}

请直接输出摘要，不要加标题或前缀。语言要通俗，让没有专业背景的人也能看懂。"""

    return _call_llm(prompt)


def _call_llm(prompt: str) -> str:
    config = load_config()
    api_url = config.get("api_url", "")
    api_key = config.get("api_key", "")
    model = config.get("model", "")

    if not api_url or not api_key:
        return "请先在设置页面配置 AI API 地址和密钥"

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
