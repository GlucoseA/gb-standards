# GB 国家标准查询系统

一站式查询中国国家标准（GB）的 Web 应用，支持关键词搜索、语义搜索、标准日历总览和 AI 智能解读。

## 功能特性

- **标准搜索** — 按标准号、名称、关键词模糊搜索，支持状态/类型筛选
- **语义搜索** — 基于智谱 `embedding-3` 云端向量模型，理解搜索意图而非仅匹配关键词（支持增量索引构建）
- **标准日历** — 按月份查看即将生效 / 即将废止的标准
- **AI 智能解读** — 接入 LLM，一键生成标准的通俗解读
- **自动同步** — 定时从国家标准委官网增量 / 全量同步数据

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | React + Ant Design + Vite |
| 后端 | FastAPI + SQLAlchemy + SQLite |
| 语义搜索 | 智谱 embedding-3 云端 API + NumPy |
| AI 解读 | 兼容 OpenAI 格式的 LLM API（默认 DeepSeek） |

## 快速开始

### Docker 一键部署（推荐）

```bash
docker run -d \
  --name gb-standards \
  --env-file .env \
  -p 8000:8000 \
  -v gb-data:/app/data \
  --restart unless-stopped \
  gbproject/gb-standards:latest
```

镜像已包含 65000+ 条标准数据和向量索引，启动即可使用，无需额外 API 调用。

访问 `http://localhost:8000`。

### 本地开发

**后端：**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**前端：**
```bash
cd frontend
npm install
npm run dev
```

前端开发服务器访问 `http://localhost:3000`，API 请求自动代理到后端 8000 端口。

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATA_DIR` | 数据目录（DB、向量、配置） | `/app/data`（Docker） |
| `AI_API_KEY` | LLM API 密钥 | — |
| `AI_API_URL` | LLM API 地址 | `https://api.deepseek.com/chat/completions` |
| `AI_MODEL` | 模型名称 | `deepseek-chat` |
| `EMBEDDING_API_KEY` | 智谱 Embedding API 密钥 | — |
| `EMBEDDING_API_URL` | Embedding API 地址 | `https://open.bigmodel.cn/api/paas/v4/embeddings` |
| `EMBEDDING_MODEL` | Embedding 模型 | `embedding-3` |
| `CORS_ORIGINS` | 允许的前端域名（逗号分隔） | `*` |

### 语义搜索

向量索引已预构建在 Docker 镜像中。爬取新数据后，系统自动执行**增量构建**——仅为新增标准调用 Embedding API，已有向量不会重复生成。

## 数据来源

[国家标准全文公开系统](https://openstd.samr.gov.cn) — 中国国家标准化管理委员会

## License

MIT
