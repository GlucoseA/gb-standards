import axios from 'axios'

const STORAGE_KEY = 'gb_ai_config'

function getAIHeaders() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    const cfg = JSON.parse(raw)
    if (!cfg?.api_key) return {}
    const headers = { 'X-AI-API-Key': cfg.api_key }
    if (cfg.api_url) headers['X-AI-API-URL'] = cfg.api_url
    if (cfg.model) headers['X-AI-Model'] = cfg.model
    return headers
  } catch {
    return {}
  }
}

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

export async function searchStandards({ q = '', status = '', standardType = '', page = 1, pageSize = 20 }) {
  const { data } = await api.get('/standards/search', {
    params: { q, status, standard_type: standardType, page, page_size: pageSize },
  })
  return data
}

export async function getStandardDetail(id) {
  const { data } = await api.get(`/standards/${id}`)
  return data
}

export async function getCategories() {
  const { data } = await api.get('/standards/categories')
  return data
}

export async function getUpcoming(days = 90) {
  const { data } = await api.get('/calendar/upcoming', { params: { days } })
  return data
}

export async function getExpiring(days = 90) {
  const { data } = await api.get('/calendar/expiring', { params: { days } })
  return data
}

export async function getMonthly(year, month) {
  const { data } = await api.get('/calendar/monthly', { params: { year, month } })
  return data
}

export async function getStats() {
  const { data } = await api.get('/stats')
  return data
}

export async function getScraperStatus() {
  const { data } = await api.get('/scraper/status')
  return data
}

export async function getStandardSummary(id) {
  const { data } = await api.get(`/standards/${id}/summary`, {
    timeout: 30000,
    headers: getAIHeaders(),
  })
  return data
}

export async function getLiveDetail(id) {
  const { data } = await api.get(`/standards/${id}/detail`, { timeout: 30000 })
  return data
}

// 向量搜索
export async function vectorSearch(q, topK = 20) {
  const { data } = await api.get('/vector-search', { params: { q, top_k: topK } })
  return data
}

// 测试 AI 连接
export async function testAIConnection() {
  try {
    const { data } = await api.post('/ai-test', null, {
      timeout: 30000,
      headers: getAIHeaders(),
    })
    return data
  } catch (e) {
    // 如果后端返回了 JSON 响应，优先使用
    if (e.response?.data) return e.response.data
    return { success: false, message: e.message || '连接测试失败' }
  }
}
