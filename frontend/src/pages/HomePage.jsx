import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Input, Tag, Button, Modal, Descriptions, Spin, Alert, Table, Empty } from 'antd'
import {
  SearchOutlined, SyncOutlined, RobotOutlined, LinkOutlined,
  RocketOutlined, StopOutlined, InfoCircleOutlined,
} from '@ant-design/icons'
import { getStats, getUpcoming, getExpiring, getScraperStatus, searchStandards, getLiveDetail, getStandardSummary } from '../api/client'

const { Search } = Input

const statusColor = { '现行': 'green', '即将实施': 'blue', '废止': 'red' }
const typeColor = { '强制性国家标准': 'red', '推荐性国家标准': 'blue', '指导性技术文件': 'orange' }

export default function HomePage() {
  const navigate = useNavigate()
  const [stats, setStats] = useState({ total: 0, active: 0, upcoming: 0, abolished: 0 })
  const [upcomingList, setUpcomingList] = useState([])
  const [expiringList, setExpiringList] = useState([])

  // 统计卡片筛选
  const [filterKey, setFilterKey] = useState(null)
  const [filtered, setFiltered] = useState({ items: [], total: 0 })
  const [filteredLoading, setFilteredLoading] = useState(false)
  const [filteredPage, setFilteredPage] = useState(1)
  const [filteredPageSize, setFilteredPageSize] = useState(8)

  // 详情弹窗
  const [modalOpen, setModalOpen] = useState(false)
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [summary, setSummary] = useState('')
  const [summaryLoading, setSummaryLoading] = useState(false)

  const [syncStatus, setSyncStatus] = useState(null) // { is_running, message }

  useEffect(() => {
    loadData()
    // 轮询同步状态
    checkSync()
    const interval = setInterval(checkSync, 5000)
    return () => clearInterval(interval)
  }, [])

  const checkSync = async () => {
    try {
      const s = await getScraperStatus()
      setSyncStatus(s)
      if (!s.is_running && s.total_standards > 0) {
        loadData() // 同步完成后刷新数据
      }
    } catch { /* ignore */ }
  }

  const loadData = async () => {
    try {
      const [s, u, e] = await Promise.all([getStats(), getUpcoming(180), getExpiring(180)])
      setStats(s); setUpcomingList(u); setExpiringList(e)
    } catch { /* empty */ }
  }

  const statusMap = { total: '', active: '现行', upcoming: '即将实施', abolished: '废止' }
  const labelMap = { total: '标准总数', active: '现行标准', upcoming: '即将实施', abolished: '已废止' }

  const loadFiltered = async (key, page, pageSize) => {
    setFilteredLoading(true); setFilteredPage(page)
    const size = pageSize || filteredPageSize
    try {
      const data = await searchStandards({ status: statusMap[key], page, pageSize: size })
      setFiltered(data)
    } catch { setFiltered({ items: [], total: 0 }) }
    setFilteredLoading(false)
  }

  const onStatClick = (key) => {
    if (filterKey === key) { setFilterKey(null); return }
    setFilterKey(key); loadFiltered(key, 1)
  }

  const showDetail = async (id) => {
    setModalOpen(true); setDetailLoading(true); setDetail(null); setSummary('')
    try { setDetail(await getLiveDetail(id)) } catch { setDetail(null) }
    setDetailLoading(false)
  }

  const loadSummary = async (id) => {
    setSummaryLoading(true)
    try { setSummary((await getStandardSummary(id)).summary) } catch { setSummary('生成失败') }
    setSummaryLoading(false)
  }


  const statItems = [
    { key: 'total', label: '标准总数', value: stats.total, color: '#1d2129' },
    { key: 'active', label: '现行', value: stats.active, color: '#00b42a' },
    { key: 'upcoming', label: '即将实施', value: stats.upcoming, color: '#1677ff' },
    { key: 'abolished', label: '已废止', value: stats.abolished, color: '#86909c' },
  ]

  const renderStdItem = (item, showDate) => (
    <div className="std-list-item" key={item.id} onClick={() => showDetail(item.id)}>
      <div className="std-info">
        <div className="std-number">{item.standard_number}</div>
        <div className="std-name">{item.cn_name}</div>
      </div>
      <div className="std-meta">
        {showDate && <div style={{ fontSize: 12, color: '#86909c' }}>{item.date || item.implement_date}</div>}
        <Tag color={statusColor[item.status] || 'default'} style={{ margin: 0, fontSize: 11 }}>{item.status}</Tag>
      </div>
    </div>
  )

  const filteredColumns = [
    {
      title: '标准号', dataIndex: 'standard_number', width: 170,
      render: (t, r) => <a onClick={() => showDetail(r.id)}>{t}</a>,
    },
    { title: '标准名称', dataIndex: 'cn_name', ellipsis: true },
    {
      title: '类型', dataIndex: 'standard_type', width: 130,
      render: (t) => <Tag color={typeColor[t] || 'default'} style={{ fontSize: 11 }}>{t || '-'}</Tag>,
    },
    {
      title: '状态', dataIndex: 'status', width: 90,
      render: (s) => <Tag color={statusColor[s] || 'default'}>{s}</Tag>,
    },
    { title: '实施日期', dataIndex: 'implement_date', width: 110 },
    {
      title: '', width: 60,
      render: (_, r) => <a onClick={() => showDetail(r.id)}><InfoCircleOutlined /></a>,
    },
  ]

  return (
    <div>
      {/* 搜索区 */}
      <div className="search-section">
        <h1>国家标准查询</h1>
        <p className="subtitle">查询商品适用的国家标准，了解标准动态</p>
        <Search
          placeholder="搜索商品名称、标准号或关键词，如：食品安全、儿童玩具、GB/T 1234"
          allowClear
          enterButton={<><SearchOutlined /> 搜索</>}
          size="large"
          onSearch={(v) => v && navigate(`/search?q=${encodeURIComponent(v)}`)}
        />
      </div>

      <div className="home-wrapper">
        {/* 统计条 */}
        <div className="stats-bar">
          {statItems.map(({ key, label, value, color }) => (
            <div
              key={key}
              className={`stat-item ${filterKey === key ? 'active' : ''}`}
              onClick={() => onStatClick(key)}
            >
              <span className="stat-num" style={{ color }}>{value.toLocaleString()}</span>
              <span className="stat-label">{label}</span>
            </div>
          ))}
        </div>

        {/* 点击统计后的筛选表格 */}
        {filterKey && (
          <div className="filter-panel">
            <div className="panel-header">
              <h3>{labelMap[filterKey]}</h3>
              <Button type="link" size="small" onClick={() => setFilterKey(null)}>收起</Button>
            </div>
            <div style={{ padding: '12px 16px' }}>
              <Table
                columns={filteredColumns}
                dataSource={filtered.items}
                loading={filteredLoading}
                rowKey="id"
                size="small"
                pagination={{
                  current: filteredPage, total: filtered.total, pageSize: filteredPageSize,
                  showSizeChanger: true,
                  pageSizeOptions: ['8', '10', '20', '50', '100'],
                  onChange: (p, ps) => {
                    if (ps !== filteredPageSize) { setFilteredPageSize(ps); loadFiltered(filterKey, 1, ps) }
                    else loadFiltered(filterKey, p, ps)
                  },
                  showTotal: (t) => `共 ${t} 条`, size: 'small',
                }}
              />
            </div>
          </div>
        )}

        {/* 双栏：即将生效 + 即将废止 */}
        <div className="main-grid">
          <div className="grid-card">
            <div className="card-header">
              <h3><RocketOutlined style={{ color: '#1677ff' }} /> 近期即将生效</h3>
              <Button type="link" size="small" onClick={() => navigate('/calendar?tab=upcoming')}>
                查看全部 ({upcomingList.length})
              </Button>
            </div>
            <div className="card-body">
              {upcomingList.length === 0
                ? <Empty description="暂无数据" style={{ padding: 32 }} image={Empty.PRESENTED_IMAGE_SIMPLE} />
                : upcomingList.slice(0, 8).map((item) => renderStdItem(item, true))
              }
            </div>
          </div>

          <div className="grid-card">
            <div className="card-header">
              <h3><StopOutlined style={{ color: '#f53f3f' }} /> 近期即将废止</h3>
              <Button type="link" size="small" onClick={() => navigate('/calendar?tab=expiring')}>
                查看全部 ({expiringList.length})
              </Button>
            </div>
            <div className="card-body">
              {expiringList.length === 0
                ? <Empty description="暂无即将废止的标准" style={{ padding: 32 }} image={Empty.PRESENTED_IMAGE_SIMPLE} />
                : expiringList.slice(0, 8).map((item) => renderStdItem(item, true))
              }
            </div>
          </div>
        </div>

        {/* 同步状态栏（只读） */}
        <div className="sync-bar">
          {syncStatus?.is_running ? (
            <>
              <SyncOutlined spin style={{ color: '#1677ff', fontSize: 16 }} />
              <p style={{ color: '#1677ff', fontWeight: 500 }}>{syncStatus.message || '正在同步数据...'}</p>
            </>
          ) : (
            <p>
              {syncStatus?.total_standards
                ? `已收录 ${syncStatus.total_standards.toLocaleString()} 条标准`
                : '数据自动同步中'}
              {syncStatus?.last_run && ` · 上次同步: ${new Date(syncStatus.last_run).toLocaleString('zh-CN')}`}
            </p>
          )}
        </div>
      </div>

      {/* 详情弹窗 */}
      <Modal
        title="标准详细信息"
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setSummary('') }}
        footer={null}
        width={720}
      >
        {detailLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin tip="正在获取详细信息..." /></div>
        ) : detail ? (
          <>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="标准号" span={2}>
                {detail.standard_number}
                {detail.hcno && (
                  <a href={`https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=${detail.hcno}`}
                    target="_blank" rel="noopener noreferrer" style={{ marginLeft: 12 }}>
                    <LinkOutlined /> 官网查看 / 预览PDF
                  </a>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="标准名称" span={2}>{detail.cn_name}</Descriptions.Item>
              {detail.en_name && <Descriptions.Item label="英文名称" span={2}>{detail.en_name}</Descriptions.Item>}
              <Descriptions.Item label="状态"><Tag color={statusColor[detail.status]}>{detail.status}</Tag></Descriptions.Item>
              <Descriptions.Item label="类型"><Tag color={typeColor[detail.standard_type]}>{detail.standard_type}</Tag></Descriptions.Item>
              {detail.ics_code && <Descriptions.Item label="ICS">{detail.ics_code}</Descriptions.Item>}
              {detail.ccs_code && <Descriptions.Item label="CCS">{detail.ccs_code}</Descriptions.Item>}
              <Descriptions.Item label="发布日期">{detail.publish_date || '-'}</Descriptions.Item>
              <Descriptions.Item label="实施日期">{detail.implement_date || '-'}</Descriptions.Item>
              {detail.category && <Descriptions.Item label="归口部门" span={2}>{detail.category}</Descriptions.Item>}
              {detail.replaced_by && <Descriptions.Item label="替代标准" span={2}>{detail.replaced_by}</Descriptions.Item>}
            </Descriptions>

            {detail.raw_fields && Object.keys(detail.raw_fields).length > 0 && (
              <Descriptions bordered column={2} size="small" style={{ marginTop: 12 }} title="官网详细信息">
                {Object.entries(detail.raw_fields).filter(([k, v]) => v && k.length < 30).map(([k, v]) => (
                  <Descriptions.Item key={k} label={k} span={v.length > 30 ? 2 : 1}>{v}</Descriptions.Item>
                ))}
              </Descriptions>
            )}

            <div style={{ marginTop: 16 }}>
              {!summary && !summaryLoading && (
                <Button type="primary" icon={<RobotOutlined />} onClick={() => loadSummary(detail.id)}
                  block size="large" style={{ borderRadius: 8 }}>
                  AI 智能解读此标准
                </Button>
              )}
              {summaryLoading && <div style={{ textAlign: 'center', padding: 20 }}><Spin tip="AI 解读中..." /></div>}
              {summary && (
                <Alert message={<><RobotOutlined /> AI 智能解读</>} description={summary}
                  type="info" showIcon={false} style={{ marginTop: 8, borderRadius: 8 }} />
              )}
            </div>
          </>
        ) : <p>获取失败</p>}
      </Modal>
    </div>
  )
}
