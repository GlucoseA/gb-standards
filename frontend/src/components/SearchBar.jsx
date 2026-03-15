import { Input, Select, Space, Button } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { useState, useEffect, memo } from 'react'

const { Search } = Input

export default memo(function SearchBar({ onSearch, categories, loading, initialKeyword = '' }) {
  const [keyword, setKeyword] = useState(initialKeyword)
  const [status, setStatus] = useState('')
  const [type, setType] = useState('')

  useEffect(() => {
    if (initialKeyword && !keyword) setKeyword(initialKeyword)
  }, [initialKeyword])

  const handleSearch = (value, overrides = {}) => {
    const params = {
      q: value ?? keyword,
      status: overrides.status ?? status,
      standardType: overrides.standardType ?? type,
    }
    onSearch(params)
  }

  return (
    <Space wrap size="middle" style={{ marginBottom: 16, width: '100%' }}>
      <Search
        placeholder="输入商品名称、标准号或关键词搜索"
        allowClear
        enterButton={<><SearchOutlined /> 搜索</>}
        size="large"
        style={{ width: 420 }}
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        onSearch={(v) => handleSearch(v)}
        loading={loading}
      />
      <Select
        placeholder="标准状态"
        allowClear
        style={{ width: 140 }}
        size="large"
        value={status || undefined}
        onChange={(v) => { const val = v || ''; setStatus(val); handleSearch(keyword, { status: val }) }}
        options={(categories?.statuses || []).map((s) => ({ label: s, value: s }))}
      />
      <Select
        placeholder="标准类型"
        allowClear
        style={{ width: 140 }}
        size="large"
        value={type || undefined}
        onChange={(v) => { const val = v || ''; setType(val); handleSearch(keyword, { standardType: val }) }}
        options={(categories?.types || []).map((t) => ({ label: t, value: t }))}
      />
    </Space>
  )
})
