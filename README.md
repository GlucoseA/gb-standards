# GB 国家标准爬虫服务

自动爬取中国国家标准（GB）数据的后端服务，支持增量/全量定时同步。

## 功能特性

- **数据爬取** — 从国家标准委官网（openstd.samr.gov.cn）爬取标准列表和详情
- **自动同步** — 启动时自动同步，定时增量（12h）/ 全量（7d）同步
- **数据存储** — SQLite 数据库，按标准号去重，支持增量更新
- **状态查询** — API 接口查询爬虫状态和标准统计

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | FastAPI + SQLAlchemy + SQLite |
| 爬虫 | Requests + BeautifulSoup + lxml |

## 快速开始

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## API 接口

| 接口 | 说明 |
|------|------|
| `GET /api/stats` | 标准统计（总数、现行、即将实施、废止） |
| `GET /api/scraper/status` | 爬虫运行状态 |

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATA_DIR` | 数据目录（存放 SQLite DB） | 项目 backend 目录 |
| `CORS_ORIGINS` | 允许的 CORS 域名 | `*` |

## 数据来源

[国家标准全文公开系统](https://openstd.samr.gov.cn) — 中国国家标准化管理委员会

## License

MIT
