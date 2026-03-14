import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Card, Tabs, Table, Tag, Select, Space, Modal, Descriptions, Spin, Button, Alert } from 'antd'
import { RocketOutlined, CheckCircleOutlined, StopOutlined, RobotOutlined, InfoCircleOutlined, LinkOutlined } from '@ant-design/icons'
import { searchStandards, getUpcoming, getExpiring, getLiveDetail, getStandardSummary } from '../api/client'

const statusColorMap = {
  '现行': 'green',
  '即将实施': 'blue',
  '废止': 'red',
}

export default function CalendarPage() {
  const [searchParams] = useSearchParams()
  const initialTab = searchParams.get('tab') || 'upcoming'
  const [activeTab, setActiveTab] = useState(initialTab)
  const [days, setDays] = useState(90)
  const [expiringDays, setExpiringDays] = useState(365)

  const [upcomingData, setUpcomingData] = useState([])
  const [upcomingLoading, setUpcomingLoading] = useState(false)
  const [upcomingPageSize, setUpcomingPageSize] = useState(20)

  const [expiringData, setExpiringData] = useState([])
  const [expiringLoading, setExpiringLoading] = useState(false)
  const [expiringPageSize, setExpiringPageSize] = useState(20)

  const [activeData, setActiveData] = useState({ items: [], total: 0 })
  const [activeLoading, setActiveLoading] = useState(false)
  const [activePage, setActivePage] = useState(1)
  const [activePageSize, setActivePageSize] = useState(20)

  // 详情弹窗
  const [modalOpen, setModalOpen] = useState(false)
  const [liveDetail, setLiveDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [summary, setSummary] = useState('')
  const [summaryLoading, setSummaryLoading] = useState(false)

  useEffect(() => {
    if (activeTab === 'upcoming') loadUpcoming(days)
  }, [days, activeTab])

  useEffect(() => {
    if (activeTab === 'expiring') loadExpiring(expiringDays)
  }, [expiringDays, activeTab])

  useEffect(() => {
    if (activeTab === 'active') loadActive(activePage, activePageSize)
  }, [activeTab])

  const loadUpcoming = async (d) => {
    setUpcomingLoading(true)
    try {
      const data = await getUpcoming(d)
      setUpcomingData(data)
    } catch { setUpcomingData([]) }
    setUpcomingLoading(false)
  }

  const loadExpiring = async (d) => {
    setExpiringLoading(true)
    try {
      const data = await getExpiring(d)
      setExpiringData(data)
    } catch { setExpiringData([]) }
    setExpiringLoading(false)
  }

  const loadActive = async (page, pageSize) => {
    setActiveLoading(true)
    const size = pageSize || activePageSize
    try {
      const data = await searchStandards({ status: '现行', page, pageSize: size })
      setActiveData(data)
    } catch { setActiveData({ items: [], total: 0 }) }
    setActiveLoading(false)
  }

  const showDetail = async (id) => {
    setModalOpen(true)
    setDetailLoading(true)
    setLiveDetail(null)
    setSummary('')
    try {
      const d = await getLiveDetail(id)
      setLiveDetail(d)
    } catch { setLiveDetail(null) }
    setDetailLoading(false)
  }

  const loadSummary = async (id) => {
    setSummaryLoading(true)
    try {
      const res = await getStandardSummary(id)
      setSummary(res.summary)
    } catch { setSummary('AI 摘要生成失败，请稍后重试') }
    setSummaryLoading(false)
  }

  const baseColumns = [
    {
      title: '标准号',
      dataIndex: 'standard_number',
      key: 'standard_number',
      width: 180,
      render: (text, record) => (
        <a onClick={() => showDetail(record.id)}>{text}</a>
      ),
    },
    {
      title: '标准名称',
      dataIndex: 'cn_name',
      key: 'cn_name',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (s) => <Tag color={statusColorMap[s] || 'default'}>{s}</Tag>,
    },
    {
      title: '类型',
      dataIndex: 'standard_type',
      key: 'standard_type',
      width: 130,
      render: (t) => {
        const colorMap = { '强制性国家标准': 'red', '推荐性国家标准': 'blue', '指导性技术文件': 'orange' }
        return <Tag color={colorMap[t] || 'default'}>{t || '-'}</Tag>
      },
    },
    {
      title: '发布日期',
      dataIndex: 'publish_date',
      key: 'publish_date',
      width: 120,
    },
    {
      title: '实施日期',
      dataIndex: 'implement_date',
      key: 'implement_date',
      width: 120,
    },
  ]

  const upcomingColumns = [
    ...baseColumns,
    {
      title: '距生效',
      key: 'countdown',
      width: 100,
      render: (_, record) => {
        const date = record.date || record.implement_date
        if (!date) return '-'
        const diff = Math.ceil((new Date(date) - new Date()) / (1000 * 60 * 60 * 24))
        if (diff <= 7) return <Tag color="red">{diff} 天</Tag>
        if (diff <= 30) return <Tag color="orange">{diff} 天</Tag>
        return <Tag>{diff} 天</Tag>
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_, record) => (
        <a onClick={() => showDetail(record.id)}>
          <InfoCircleOutlined /> 详情
        </a>
      ),
    },
  ]

  const expiringColumns = [
    ...baseColumns,
    {
      title: '距废止',
      key: 'countdown',
      width: 100,
      render: (_, record) => {
        const date = record.date || record.abolish_date || record.implement_date
        if (!date) return '-'
        const diff = Math.ceil((new Date(date) - new Date()) / (1000 * 60 * 60 * 24))
        if (diff < 0) return <Tag color="red">已废止</Tag>
        if (diff <= 7) return <Tag color="red">{diff} 天</Tag>
        if (diff <= 30) return <Tag color="orange">{diff} 天</Tag>
        return <Tag>{diff} 天</Tag>
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_, record) => (
        <a onClick={() => showDetail(record.id)}>
          <InfoCircleOutlined /> 详情
        </a>
      ),
    },
  ]

  const activeColumns = [
    ...baseColumns,
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_, record) => (
        <a onClick={() => showDetail(record.id)}>
          <InfoCircleOutlined /> 详情
        </a>
      ),
    },
  ]

  const daysSelector = (value, onChange) => (
    <Space style={{ marginBottom: 16 }}>
      <span>时间范围：</span>
      <Select
        value={value}
        onChange={onChange}
        style={{ width: 140 }}
        options={[
          { label: '30 天内', value: 30 },
          { label: '90 天内', value: 90 },
          { label: '180 天内', value: 180 },
          { label: '365 天内', value: 365 },
        ]}
      />
    </Space>
  )

  const tabItems = [
    {
      key: 'upcoming',
      label: <><RocketOutlined /> 即将生效</>,
      children: (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            {daysSelector(days, setDays)}
            <span style={{ color: '#999', fontSize: 13 }}>
              共 {upcomingData.length} 条标准即将生效
            </span>
          </div>
          <Table
            columns={upcomingColumns}
            dataSource={upcomingData}
            loading={upcomingLoading}
            rowKey="id"
            pagination={{
              pageSize: upcomingPageSize,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50', '100'],
              showTotal: (t) => `共 ${t} 条`,
              onShowSizeChange: (_, size) => setUpcomingPageSize(size),
            }}
          />
        </>
      ),
    },
    {
      key: 'expiring',
      label: <><StopOutlined /> 即将废止</>,
      children: (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            {daysSelector(expiringDays, setExpiringDays)}
            <span style={{ color: '#999', fontSize: 13 }}>
              共 {expiringData.length} 条标准即将废止
            </span>
          </div>
          <Table
            columns={expiringColumns}
            dataSource={expiringData}
            loading={expiringLoading}
            rowKey="id"
            pagination={{
              pageSize: expiringPageSize,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50', '100'],
              showTotal: (t) => `共 ${t} 条`,
              onShowSizeChange: (_, size) => setExpiringPageSize(size),
            }}
          />
        </>
      ),
    },
    {
      key: 'active',
      label: <><CheckCircleOutlined /> 现行标准</>,
      children: (
        <>
          <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', marginBottom: 16 }}>
            <span style={{ color: '#999', fontSize: 13 }}>
              共 {activeData.total} 条现行标准
            </span>
          </div>
          <Table
            columns={activeColumns}
            dataSource={activeData.items}
            loading={activeLoading}
            rowKey="id"
            pagination={{
              current: activePage,
              total: activeData.total,
              pageSize: activePageSize,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50', '100'],
              showTotal: (t) => `共 ${t} 条`,
              onChange: (p, ps) => {
                if (ps !== activePageSize) { setActivePageSize(ps); setActivePage(1); loadActive(1, ps) }
                else { setActivePage(p); loadActive(p, ps) }
              },
            }}
          />
        </>
      ),
    },
  ]

  // 详情弹窗中展示从官网实时爬取的原始字段
  const renderRawFields = (rawFields) => {
    if (!rawFields || Object.keys(rawFields).length === 0) return null
    const entries = Object.entries(rawFields).filter(([k, v]) => v && k.length < 30)
    return (
      <Descriptions bordered column={2} size="small" style={{ marginTop: 16 }}>
        {entries.map(([key, value]) => (
          <Descriptions.Item key={key} label={key} span={value.length > 30 ? 2 : 1}>
            {value}
          </Descriptions.Item>
        ))}
      </Descriptions>
    )
  }

  return (
    <div className="page-container">
      <h2 className="section-title">标准状态总览</h2>
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>

      <Modal
        title="标准详细信息"
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setSummary('') }}
        footer={null}
        width={750}
      >
        {detailLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin tip="正在从国标委官网获取详细信息..." />
          </div>
        ) : liveDetail ? (
          <>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="标准号" span={2}>
                {liveDetail.standard_number}
                {liveDetail.hcno && (
                  <a
                    href={`https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=${liveDetail.hcno}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ marginLeft: 12 }}
                  >
                    <LinkOutlined /> 官网查看
                  </a>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="标准名称" span={2}>
                {liveDetail.cn_name}
              </Descriptions.Item>
              {liveDetail.en_name && (
                <Descriptions.Item label="英文名称" span={2}>
                  {liveDetail.en_name}
                </Descriptions.Item>
              )}
              <Descriptions.Item label="状态">
                <Tag color={statusColorMap[liveDetail.status] || 'default'}>
                  {liveDetail.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="类型">{liveDetail.standard_type}</Descriptions.Item>
              <Descriptions.Item label="发布日期">{liveDetail.publish_date || '-'}</Descriptions.Item>
              <Descriptions.Item label="实施日期">{liveDetail.implement_date || '-'}</Descriptions.Item>
              {liveDetail.ics_code && (
                <Descriptions.Item label="ICS 分类">{liveDetail.ics_code}</Descriptions.Item>
              )}
              {liveDetail.ccs_code && (
                <Descriptions.Item label="CCS 分类">{liveDetail.ccs_code}</Descriptions.Item>
              )}
              {liveDetail.category && (
                <Descriptions.Item label="归口部门" span={2}>{liveDetail.category}</Descriptions.Item>
              )}
              {liveDetail.replaced_by && (
                <Descriptions.Item label="替代标准" span={2}>{liveDetail.replaced_by}</Descriptions.Item>
              )}
              {liveDetail.abolish_date && (
                <Descriptions.Item label="废止日期">{liveDetail.abolish_date}</Descriptions.Item>
              )}
            </Descriptions>

            {liveDetail.raw_fields && Object.keys(liveDetail.raw_fields).length > 0 && (
              <>
                <h4 style={{ marginTop: 16, marginBottom: 8, color: '#666' }}>
                  官网原始信息
                </h4>
                {renderRawFields(liveDetail.raw_fields)}
              </>
            )}

            <div style={{ marginTop: 16 }}>
              {!summary && !summaryLoading && (
                <Button
                  type="primary"
                  icon={<RobotOutlined />}
                  onClick={() => loadSummary(liveDetail.id)}
                  block
                  size="large"
                >
                  AI 智能解读此标准
                </Button>
              )}
              {summaryLoading && (
                <div style={{ textAlign: 'center', padding: 20 }}>
                  <Spin tip="AI 正在结合详细信息解读标准..." />
                </div>
              )}
              {summary && (
                <Alert
                  message={<><RobotOutlined /> AI 智能解读</>}
                  description={summary}
                  type="info"
                  showIcon={false}
                  style={{ marginTop: 8 }}
                />
              )}
            </div>
          </>
        ) : (
          <p>获取详细信息失败</p>
        )}
      </Modal>
    </div>
  )
}
