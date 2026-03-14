import axios from 'axios'

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
  const { data } = await api.get(`/standards/${id}/summary`, { timeout: 30000 })
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
