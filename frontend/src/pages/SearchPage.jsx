import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Card, Tag, Alert, Switch } from 'antd'
import { ThunderboltOutlined } from '@ant-design/icons'
import SearchBar from '../components/SearchBar'
import StandardTable from '../components/StandardTable'
import { searchStandards, getCategories, vectorSearch } from '../api/client'

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [results, setResults] = useState({ items: [], total: 0, page: 1, page_size: 20 })
  const [loading, setLoading] = useState(false)
  const [categories, setCategories] = useState({ statuses: [], types: [] })
  const [searchState, setSearchState] = useState({
    q: searchParams.get('q') || '',
    status: '',
    standardType: '',
  })
  const skipEffectRef = useRef(false)
  const [semanticOn, setSemanticOn] = useState(true)
  const [semanticResults, setSemanticResults] = useState(null) // { items, total }
  const [allSemanticResults, setAllSemanticResults] = useState(null) // 保存未过滤的语义结果
  const [semanticLoading, setSemanticLoading] = useState(false)

  useEffect(() => {
    getCategories().then(setCategories).catch(() => {})
  }, [])

  useEffect(() => {
    if (skipEffectRef.current) {
      skipEffectRef.current = false
      return
    }
    const q = searchParams.get('q')
    if (q) {
      doSearch({ q, status: '', standardType: '' }, 1)
    }
  }, [searchParams])

  const [pageSize, setPageSize] = useState(20)

  const filterSemanticResults = (allItems, params, keywordResultItems) => {
    if (!allItems || allItems.length === 0) return null
    let filtered = allItems
    if (params.status) filtered = filtered.filter(i => i.status === params.status)
    if (params.standardType) filtered = filtered.filter(i => i.standard_type === params.standardType)
    // 去掉与关键词搜索重复的结果
    const keywordIds = new Set((keywordResultItems || []).map(i => i.id))
    filtered = filtered.filter(i => !keywordIds.has(i.id))
    return filtered.length > 0 ? { items: filtered, total: filtered.length } : null
  }

  const doSearch = async (params, page = 1, ps) => {
    setLoading(true)
    setSearchState(params)
    const size = ps || pageSize
    try {
      const data = await searchStandards({ ...params, page, pageSize: size })
      setResults(data)

      // 语义搜索：仅在关键词变化或首次搜索时重新请求
      if (params.q && semanticOn) {
        const isNewQuery = !allSemanticResults || params.q !== searchState.q
        if (isNewQuery) {
          setSemanticLoading(true)
          try {
            const vr = await vectorSearch(params.q, 10)
            if (vr.items && vr.items.length > 0) {
              setAllSemanticResults(vr.items)
              setSemanticResults(filterSemanticResults(vr.items, params, data.items))
            } else {
              setAllSemanticResults(null)
              setSemanticResults(null)
            }
          } catch {
            setAllSemanticResults(null)
            setSemanticResults(null)
          }
          setSemanticLoading(false)
        } else {
          // 关键词没变，只是切换了筛选条件，客户端过滤语义结果
          setSemanticResults(filterSemanticResults(allSemanticResults, params, data.items))
        }
      } else {
        setSemanticResults(null)
      }
    } catch {
      setResults({ items: [], total: 0, page: 1, page_size: size })
    }
    setLoading(false)
  }

  const handleSearch = (params) => {
    skipEffectRef.current = true
    setSearchParams(params.q ? { q: params.q } : {})
    doSearch(params, 1)
  }

  const handlePageChange = (page, ps) => {
    if (ps !== pageSize) { setPageSize(ps); doSearch(searchState, 1, ps) }
    else doSearch(searchState, page, ps)
  }

  return (
    <div className="page-container">
      <h2 className="section-title">标准查询</h2>
      <Card style={{ marginBottom: 16 }}>
        <SearchBar onSearch={handleSearch} categories={categories} loading={loading} initialKeyword={searchState.q} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
          <Switch
            size="small"
            checked={semanticOn}
            onChange={setSemanticOn}
          />
          <span style={{ fontSize: 13, color: '#86909c' }}>
            <ThunderboltOutlined /> 语义搜索（需先在 AI 设置中构建索引）
          </span>
        </div>
      </Card>

      {/* 语义搜索额外结果 */}
      {semanticResults && semanticResults.items.length > 0 && (
        <Card
          size="small"
          style={{ marginBottom: 16 }}
          title={
            <span style={{ fontSize: 14 }}>
              <ThunderboltOutlined style={{ color: '#722ed1' }} /> 语义匹配结果
              <Tag color="purple" style={{ marginLeft: 8 }}>AI</Tag>
              <span style={{ fontSize: 12, color: '#86909c', fontWeight: 400, marginLeft: 4 }}>
                以下标准与您的搜索语义相关
              </span>
            </span>
          }
        >
          <StandardTable
            data={semanticResults.items}
            loading={semanticLoading}
            pagination={false}
          />
        </Card>
      )}

      <Card>
        <StandardTable
          data={results.items}
          loading={loading}
          pagination={{ page: results.page, total: results.total, pageSize: results.page_size }}
          onPageChange={handlePageChange}
        />
      </Card>
    </div>
  )
}
