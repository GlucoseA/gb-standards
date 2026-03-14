"""
国家标准委官网爬虫
数据来源: https://openstd.samr.gov.cn/bzgk/gb/std_list
"""

import re
import time
import logging
import threading
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
from sqlalchemy.orm import Session

from ..models import Standard
from ..database import SessionLocal, init_db

logger = logging.getLogger(__name__)

BASE_URL = "https://openstd.samr.gov.cn/bzgk/gb"
LIST_URL = f"{BASE_URL}/std_list"
DETAIL_URL = f"{BASE_URL}/newGbInfo"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 爬虫状态
_scraper_lock = threading.Lock()
scraper_state = {
    "is_running": False,
    "last_run": None,
    "message": "未运行",
}


def parse_date(date_str: str) -> date | None:
    """解析日期字符串，支持多种格式"""
    if not date_str or not date_str.strip():
        return None
    date_str = date_str.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y年%m月%d日"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


# 标准类型映射: p.p1 参数值 -> 中文名称
STANDARD_TYPES = {
    0: "",       # 全部
    1: "强制性国家标准",
    2: "推荐性国家标准",
    3: "指导性技术文件",
}


def fetch_list_page(page: int = 1, page_size: int = 50, keyword: str = "",
                    std_type: int = 0) -> list[dict]:
    """爬取标准列表页
    std_type: 0=全部, 1=强制性, 2=推荐性, 3=指导性技术文件
    """
    params = {
        "p.p1": std_type,
        "p.p90": "circulation_date",
        "p.p91": "desc",
        "page": page,
        "pageSize": page_size,
    }
    if keyword:
        params["p.p2"] = keyword

    try:
        resp = requests.get(LIST_URL, params=params, headers=HEADERS, timeout=30)
        resp.encoding = "utf-8"
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"请求列表页失败 (page={page}): {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    results = []

    # 查找数据表格 — 包含9列(序号/标准号/是否采标/标准名称/类别/状态/发布日期/实施日期/操作)
    tables = soup.find_all("table")
    table = None
    for t in tables:
        header_row = t.find("tr")
        if header_row:
            cells = header_row.find_all(["th", "td"])
            if len(cells) >= 8:
                table = t
                break
    if not table:
        logger.warning(f"未找到结果表格 (page={page})")
        return []

    rows = table.find_all("tr")[1:]  # 跳过表头
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 8:
            continue

        # 提取 hcno (从 <a> 标签的 onclick 属性)
        hcno = ""
        link = row.find("a", onclick=True)
        if link:
            onclick = link.get("onclick", "")
            match_link = re.search(r"showInfo\(['\"]([^'\"]+)['\"]\)", onclick)
            if match_link:
                hcno = match_link.group(1)
        match = re.search(r"showInfo\(['\"]?([^'\")\s]+)['\"]?\)", row.get("onclick", ""))
        if match:
            hcno = match.group(1)

        standard = {
            "hcno": hcno,
            "standard_number": cols[1].get_text(strip=True),
            "cn_name": cols[3].get_text(strip=True),
            "standard_type": cols[4].get_text(strip=True),
            "status": cols[5].get_text(strip=True),
            "publish_date": parse_date(cols[6].get_text(strip=True)),
            "implement_date": parse_date(cols[7].get_text(strip=True)),
        }
        results.append(standard)

    return results


def fetch_detail(hcno: str) -> dict:
    """爬取标准详情页，返回所有字段（包括原始键值对）"""
    try:
        resp = requests.get(DETAIL_URL, params={"hcno": hcno}, headers=HEADERS, timeout=30)
        resp.encoding = "utf-8"
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"请求详情页失败 (hcno={hcno}): {e}")
        return {}

    soup = BeautifulSoup(resp.text, "lxml")
    detail = {}
    raw_fields = {}  # 保存所有原始字段供 AI 使用

    # 详情页使用 Bootstrap grid: div.title + div.content
    title_divs = soup.find_all("div", class_="title")
    for title_div in title_divs:
        label = title_div.get_text(strip=True)
        # 找同一行的 content div
        content_div = title_div.find_next_sibling("div", class_="content")
        if not content_div:
            parent = title_div.parent
            if parent:
                content_div = title_div.find_next("div", class_="content")
        if not content_div:
            continue
        value = content_div.get_text(strip=True)
        if not label or not value:
            continue

        raw_fields[label] = value

        # 映射到数据库字段
        if "ICS" in label:
            detail["ics_code"] = value
        elif "CCS" in label or "中标分类" in label:
            detail["ccs_code"] = value
        elif "发布日期" in label:
            detail["publish_date"] = parse_date(value)
        elif "实施日期" in label:
            detail["implement_date"] = parse_date(value)
        elif "废止日期" in label:
            detail["abolish_date"] = parse_date(value)
        elif "代替" in label or "替代" in label:
            detail["replaced_by"] = value
        elif "归口部门" in label:
            detail["category"] = value
        elif "英文" in label and "名称" in label:
            detail["en_name"] = value

    # 也尝试从 table 提取（兼容旧版页面）
    for row in soup.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True)
            if label and value:
                raw_fields[label] = value

    detail["_raw_fields"] = raw_fields
    return detail


def get_total_pages(page_size: int = 50, std_type: int = 0) -> int:
    """获取指定类型的总页数"""
    try:
        resp = requests.get(
            LIST_URL,
            params={"p.p1": std_type, "p.p90": "circulation_date", "p.p91": "desc", "pageSize": page_size},
            headers=HEADERS,
            timeout=30,
        )
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")
        text = soup.get_text()
        match = re.search(r"共\s*(\d+)\s*条", text)
        if match:
            total = int(match.group(1))
            return (total + page_size - 1) // page_size
    except Exception as e:
        logger.error(f"获取总页数失败: {e}")
    return 1


def save_standards(db: Session, standards: list[dict]):
    """批量保存标准到数据库（先查已有 hcno 集合，减少逐条查询）"""
    if not standards:
        return 0

    hcnos = [s["hcno"] for s in standards if s.get("hcno")]
    if not hcnos:
        return 0

    # 批量查已有记录，避免 N+1
    existing_map = {}
    for row in db.query(Standard).filter(Standard.hcno.in_(hcnos)).all():
        existing_map[row.hcno] = row

    new_count = 0
    now = datetime.now()

    for data in standards:
        hcno = data.get("hcno")
        if not hcno:
            continue

        existing = existing_map.get(hcno)
        if existing:
            for key, value in data.items():
                if value is not None and value != "":
                    setattr(existing, key, value)
            existing.scraped_at = now
        else:
            standard = Standard(**data, scraped_at=now)
            db.add(standard)
            new_count += 1

    db.commit()
    return new_count


import random as _random


def run_scraper(max_pages: int = 0, fetch_details: bool = True, delay: float = 1.0,
                std_types: list[int] | None = None):
    """
    运行爬虫，分类型爬取
    max_pages: 每种类型的最大爬取页数，0 表示全部
    std_types: 要爬取的类型列表 [1,2,3]，None 表示全部三种
    """
    global scraper_state
    with _scraper_lock:
        if scraper_state["is_running"]:
            logger.warning("爬虫已在运行中，跳过")
            return
        scraper_state["is_running"] = True
        scraper_state["message"] = "正在爬取..."

    if std_types is None:
        std_types = [1, 2, 3]

    init_db()
    db = SessionLocal()

    # 先统计各类型总页数，计算整体进度
    type_pages = {}
    for st in std_types:
        tp = get_total_pages(page_size=50, std_type=st)
        if max_pages > 0:
            tp = min(tp, max_pages)
        type_pages[st] = tp

    grand_total_pages = sum(type_pages.values())
    pages_done = 0
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 10

    try:
        total_saved = 0

        for std_type in std_types:
            type_name = STANDARD_TYPES.get(std_type, f"类型{std_type}")
            total_pages = type_pages[std_type]

            logger.info(f"开始爬取【{type_name}】，共 {total_pages} 页")

            for page in range(1, total_pages + 1):
                pct = int(pages_done / grand_total_pages * 100) if grand_total_pages else 0
                scraper_state["message"] = (
                    f"[{pct}%] 正在爬取【{type_name}】第 {page}/{total_pages} 页 "
                    f"(总进度 {pages_done}/{grand_total_pages}，已入库 {total_saved} 条)"
                )

                standards = fetch_list_page(page=page, std_type=std_type)

                if not standards:
                    consecutive_errors += 1
                    logger.warning(f"第 {page} 页无数据 (连续失败 {consecutive_errors})")
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        logger.error(f"连续 {MAX_CONSECUTIVE_ERRORS} 页无数据，可能被限流，暂停 30s")
                        scraper_state["message"] = f"[{pct}%] 被限流，暂停 30s 后重试..."
                        time.sleep(30)
                        consecutive_errors = 0
                    else:
                        time.sleep(delay * 2)
                    pages_done += 1
                    continue

                consecutive_errors = 0

                for std in standards:
                    if std_type in STANDARD_TYPES:
                        std["standard_type"] = STANDARD_TYPES[std_type]

                if fetch_details:
                    for std in standards:
                        if std.get("hcno"):
                            detail = fetch_detail(std["hcno"])
                            detail.pop("_raw_fields", None)
                            std.update(detail)
                            time.sleep(delay * 0.5)

                save_standards(db, standards)
                total_saved += len(standards)
                pages_done += 1

                # 自适应延迟：随机化 + 每 50 页多休息一下
                jitter = delay + _random.uniform(0, delay * 0.5)
                if pages_done % 50 == 0:
                    logger.info(f"已完成 {pages_done} 页，短暂休息 5s...")
                    time.sleep(5)
                else:
                    time.sleep(jitter)

        with _scraper_lock:
            scraper_state["message"] = f"爬取完成，共保存 {total_saved} 条标准"
            scraper_state["last_run"] = datetime.now()
        logger.info(f"爬取完成，共保存 {total_saved} 条标准")

    except Exception as e:
        with _scraper_lock:
            scraper_state["message"] = f"爬取失败: {str(e)}（已保存 {total_saved} 条）"
        logger.error(f"爬取失败: {e}", exc_info=True)
    finally:
        with _scraper_lock:
            scraper_state["is_running"] = False
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    # 默认每种类型爬取前 3 页
    run_scraper(max_pages=3, fetch_details=False, delay=1.0)
