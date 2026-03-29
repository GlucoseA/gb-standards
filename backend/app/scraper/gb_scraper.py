"""
国家标准委官网爬虫 — PDF 下载版
数据来源: https://openstd.samr.gov.cn/bzgk/gb/std_list
PDF来源:  http://c.gb688.cn/bzgk/gb/showGb -> viewGb
"""

import os
import re
import time
import logging
import threading
import random
import requests
import ddddocr
from bs4 import BeautifulSoup
from datetime import datetime, date
from pathlib import Path
from sqlalchemy.orm import Session

from ..models import Standard
from ..database import SessionLocal, init_db

logger = logging.getLogger(__name__)

BASE_URL = "https://openstd.samr.gov.cn/bzgk/gb"
LIST_URL = f"{BASE_URL}/std_list"
DETAIL_URL = f"{BASE_URL}/newGbInfo"
PDF_HOST = "http://c.gb688.cn/bzgk/gb"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# PDF 存储目录
_data_dir = os.getenv("DATA_DIR", os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
PDF_DIR = Path(_data_dir) / "pdfs"
PDF_DIR.mkdir(parents=True, exist_ok=True)

# 爬虫状态
_scraper_lock = threading.Lock()
scraper_state = {
    "is_running": False,
    "last_run": None,
    "message": "未运行",
}

# 标准类型映射: p.p1 参数值 -> 中文名称
STANDARD_TYPES = {
    0: "",       # 全部
    1: "强制性国家标准",
    2: "推荐性国家标准",
    3: "指导性技术文件",
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


def _sanitize_filename(name: str) -> str:
    """将标准编号转为安全文件名"""
    # GB/T 1234-2024 -> GB_T_1234-2024
    name = name.replace("/", "_").replace("\\", "_")
    name = re.sub(r'[<>:"|?*\s]+', "_", name)
    return name.strip("_")


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
    """爬取标准详情页，返回所有字段"""
    try:
        resp = requests.get(DETAIL_URL, params={"hcno": hcno}, headers=HEADERS, timeout=30)
        resp.encoding = "utf-8"
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"请求详情页失败 (hcno={hcno}): {e}")
        return {}

    soup = BeautifulSoup(resp.text, "lxml")
    detail = {}

    title_divs = soup.find_all("div", class_="title")
    for title_div in title_divs:
        label = title_div.get_text(strip=True)
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


# ========== PDF 下载 ==========

def _solve_captcha(session: requests.Session) -> bool:
    """获取并识别验证码，返回是否成功"""
    ocr = ddddocr.DdddOcr(show_ad=False)
    for attempt in range(5):
        try:
            resp = session.get(f"{PDF_HOST}/gc", timeout=15)
            if resp.status_code != 200 or len(resp.content) < 100:
                continue
            code = ocr.classification(resp.content)
            if not code or len(code) < 3:
                continue

            resp_verify = session.post(
                f"{PDF_HOST}/verifyCode",
                data={"verifyCode": code},
                timeout=15,
            )
            if resp_verify.text.strip() == "success":
                logger.debug(f"验证码识别成功 (attempt {attempt+1}): {code}")
                return True
            logger.debug(f"验证码识别失败 (attempt {attempt+1}): {code}")
        except Exception as e:
            logger.warning(f"验证码流程异常: {e}")
        time.sleep(0.5)
    return False


def download_pdf(hcno: str, standard_number: str) -> tuple[str, int]:
    """下载单个标准的 PDF 文件
    返回 (保存路径, 文件大小) 或 ("", 0) 表示失败
    """
    filename = _sanitize_filename(standard_number) + ".pdf"
    filepath = PDF_DIR / filename

    # 已下载则跳过
    if filepath.exists() and filepath.stat().st_size > 1000:
        return str(filepath), filepath.stat().st_size

    session = requests.Session()
    session.headers.update(HEADERS)
    session.headers["Referer"] = f"{PDF_HOST}/showGb?type=online&hcno={hcno}"

    # 访问在线阅读页以建立会话
    try:
        session.get(f"{PDF_HOST}/showGb?type=online&hcno={hcno}", timeout=30)
    except requests.RequestException as e:
        logger.error(f"访问阅读页失败 ({standard_number}): {e}")
        return "", 0

    # 识别验证码
    if not _solve_captcha(session):
        logger.warning(f"验证码识别失败，跳过 {standard_number}")
        return "", 0

    # 下载 PDF
    try:
        resp = session.get(f"{PDF_HOST}/viewGb?hcno={hcno}", timeout=120)
        if resp.status_code != 200:
            logger.warning(f"PDF 下载返回 {resp.status_code} ({standard_number})")
            return "", 0
        if len(resp.content) < 1000 or not resp.content.startswith(b"%PDF"):
            logger.warning(f"PDF 内容无效 ({standard_number}), size={len(resp.content)}")
            return "", 0

        filepath.write_bytes(resp.content)
        logger.info(f"PDF 下载成功: {filename} ({len(resp.content)} bytes)")
        return str(filepath), len(resp.content)

    except requests.RequestException as e:
        logger.error(f"PDF 下载失败 ({standard_number}): {e}")
        return "", 0


def run_scraper(max_pages: int = 0, fetch_details: bool = True, delay: float = 1.0,
                std_types: list[int] | None = None, download_pdfs: bool = False):
    """
    运行爬虫，分类型爬取
    max_pages: 每种类型的最大爬取页数，0 表示全部
    std_types: 要爬取的类型列表 [1,2,3]，None 表示全部三种
    download_pdfs: 是否下载 PDF 文件
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

    # 先统计各类型总页数
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
        pdf_downloaded = 0
        pdf_failed = 0

        for std_type in std_types:
            type_name = STANDARD_TYPES.get(std_type, f"类型{std_type}")
            total_pages = type_pages[std_type]

            logger.info(f"开始爬取【{type_name}】，共 {total_pages} 页")

            for page in range(1, total_pages + 1):
                pct = int(pages_done / grand_total_pages * 100) if grand_total_pages else 0
                pdf_msg = f"，PDF已下载 {pdf_downloaded}" if download_pdfs else ""
                scraper_state["message"] = (
                    f"[{pct}%] 正在爬取【{type_name}】第 {page}/{total_pages} 页 "
                    f"(总进度 {pages_done}/{grand_total_pages}，已入库 {total_saved} 条{pdf_msg})"
                )

                standards = fetch_list_page(page=page, std_type=std_type)

                if not standards:
                    consecutive_errors += 1
                    logger.warning(f"第 {page} 页无数据 (连续失败 {consecutive_errors})")
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        logger.error(f"连续 {MAX_CONSECUTIVE_ERRORS} 页无数据，暂停 30s")
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
                            std.update(detail)
                            time.sleep(delay * 0.5)

                save_standards(db, standards)
                total_saved += len(standards)

                # PDF 下载
                if download_pdfs:
                    for std in standards:
                        hcno = std.get("hcno")
                        sn = std.get("standard_number", "")
                        if not hcno or not sn:
                            continue

                        # 检查是否已下载
                        existing = db.query(Standard).filter(Standard.hcno == hcno).first()
                        if existing and existing.pdf_path and os.path.exists(existing.pdf_path):
                            continue

                        pdf_path, pdf_size = download_pdf(hcno, sn)
                        if pdf_path:
                            if existing:
                                existing.pdf_path = pdf_path
                                existing.pdf_size = pdf_size
                                existing.pdf_downloaded_at = datetime.now()
                                db.commit()
                            pdf_downloaded += 1
                        else:
                            pdf_failed += 1

                        # PDF 下载间隔，避免触发限流
                        time.sleep(delay + random.uniform(0.5, 1.5))

                pages_done += 1

                # 自适应延迟
                jitter = delay + random.uniform(0, delay * 0.5)
                if pages_done % 50 == 0:
                    logger.info(f"已完成 {pages_done} 页，短暂休息 5s...")
                    time.sleep(5)
                else:
                    time.sleep(jitter)

        pdf_msg = f"，PDF下载 {pdf_downloaded} 个" if download_pdfs else ""
        if pdf_failed:
            pdf_msg += f"（{pdf_failed} 个失败）"

        with _scraper_lock:
            scraper_state["message"] = f"爬取完成，共保存 {total_saved} 条标准{pdf_msg}"
            scraper_state["last_run"] = datetime.now()
        logger.info(f"爬取完成，共保存 {total_saved} 条标准{pdf_msg}")

    except Exception as e:
        with _scraper_lock:
            scraper_state["message"] = f"爬取失败: {str(e)}（已保存 {total_saved} 条）"
        logger.error(f"爬取失败: {e}", exc_info=True)
    finally:
        with _scraper_lock:
            scraper_state["is_running"] = False
        db.close()


def run_pdf_download(max_items: int = 0, delay: float = 2.0,
                     std_types: list[int] | None = None):
    """
    仅下载 PDF（对已入库但未下载 PDF 的标准）
    max_items: 最多下载数量，0 表示全部
    """
    global scraper_state
    with _scraper_lock:
        if scraper_state["is_running"]:
            logger.warning("爬虫已在运行中，跳过")
            return
        scraper_state["is_running"] = True
        scraper_state["message"] = "正在下载 PDF..."

    init_db()
    db = SessionLocal()

    try:
        # 查找未下载 PDF 的标准
        query = db.query(Standard).filter(
            (Standard.pdf_path == "") | (Standard.pdf_path.is_(None))
        )
        if std_types:
            type_names = [STANDARD_TYPES.get(t, "") for t in std_types if t in STANDARD_TYPES]
            if type_names:
                query = query.filter(Standard.standard_type.in_(type_names))

        pending = query.all()
        total = len(pending)
        if max_items > 0:
            pending = pending[:max_items]
            total = len(pending)

        logger.info(f"待下载 PDF: {total} 个")
        downloaded = 0
        failed = 0

        for i, std in enumerate(pending):
            pct = int((i + 1) / total * 100) if total else 0
            scraper_state["message"] = (
                f"[{pct}%] 正在下载 PDF ({i+1}/{total}) "
                f"{std.standard_number} — 成功 {downloaded}，失败 {failed}"
            )

            pdf_path, pdf_size = download_pdf(std.hcno, std.standard_number)
            if pdf_path:
                std.pdf_path = pdf_path
                std.pdf_size = pdf_size
                std.pdf_downloaded_at = datetime.now()
                db.commit()
                downloaded += 1
            else:
                failed += 1

            time.sleep(delay + random.uniform(0.5, 1.5))

        with _scraper_lock:
            scraper_state["message"] = f"PDF 下载完成: 成功 {downloaded}，失败 {failed}"
            scraper_state["last_run"] = datetime.now()
        logger.info(f"PDF 下载完成: 成功 {downloaded}，失败 {failed}")

    except Exception as e:
        with _scraper_lock:
            scraper_state["message"] = f"PDF 下载失败: {str(e)}"
        logger.error(f"PDF 下载失败: {e}", exc_info=True)
    finally:
        with _scraper_lock:
            scraper_state["is_running"] = False
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    # 测试：爬取 1 页 + 下载 PDF
    run_scraper(max_pages=1, fetch_details=False, delay=1.0,
                std_types=[1], download_pdfs=True)
