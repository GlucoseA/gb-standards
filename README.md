# GB 国家标准查询系统

一站式查询中国国家标准（GB）的 Web 应用，支持关键词搜索、语义搜索、标准日历总览和 AI 智能解读。

## 功能特性

- **标准搜索** — 按标准号、名称、关键词模糊搜索，支持状态/类型筛选
- **语义搜索** — 基于 `bge-base-zh-v1.5` 向量模型，理解搜索意图而非仅匹配关键词
- **标准日历** — 按月份查看即将生效 / 即将废止的标准
- **AI 智能解读** — 接入 LLM，一键生成标准的通俗解读
- **自动同步** — 定时从国家标准委官网增量 / 全量同步数据

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | React + Ant Design + Vite |
| 后端 | FastAPI + SQLAlchemy + SQLite |
| 语义搜索 | sentence-transformers (bge-base-zh-v1.5) + NumPy |
| AI 解读 | 兼容 OpenAI 格式的 LLM API |

## 快速开始

### 后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

启动后会自动从官网同步标准数据。

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:3000`。

### 环境变量（生产环境）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AI_API_KEY` | LLM API 密钥 | — |
| `AI_API_URL` | LLM API 地址 | `https://api.deepseek.com/chat/completions` |
| `AI_MODEL` | 模型名称 | `deepseek-chat` |
| `CORS_ORIGINS` | 允许的前端域名（逗号分隔） | `*` |

### 语义搜索

语义搜索需要预构建向量索引。首次使用时会自动下载约 400MB 的中文语义模型。

## 数据来源

[国家标准全文公开系统](https://openstd.samr.gov.cn) — 中国国家标准化管理委员会

## License

MIT
