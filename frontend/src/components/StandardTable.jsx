import { Table, Tag, Modal, Descriptions, Spin, Button, Alert } from 'antd'
import { RobotOutlined, LinkOutlined } from '@ant-design/icons'
import { useState, memo } from 'react'
import { getStandardDetail, getStandardSummary } from '../api/client'

const statusColorMap = {
  '现行': 'green',
  '即将实施': 'blue',
  '废止': 'red',
}

export default memo(function StandardTable({ data, loading, pagination, onPageChange }) {
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [summary, setSummary] = useState('')
  const [summaryLoading, setSummaryLoading] = useState(false)

  const showDetail = async (id) => {
    setModalOpen(true)
    setDetailLoading(true)
    setSummary('')
    try {
      const d = await getStandardDetail(id)
      setDetail(d)
    } catch {
      setDetail(null)
    }
    setDetailLoading(false)
  }

  const loadSummary = async (id) => {
    setSummaryLoading(true)
    try {
      const res = await getStandardSummary(id)
      setSummary(res.summary)
    } catch {
      setSummary('AI 摘要生成失败，请稍后重试')
    }
    setSummaryLoading(false)
  }

  const columns = [
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
      width: 120,
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

  return (
    <>
      <Table
        columns={columns}
        dataSource={data}
        loading={loading}
        rowKey="id"
        pagination={pagination === false ? false : {
          current: pagination?.page || 1,
          total: pagination?.total || 0,
          pageSize: pagination?.pageSize || 20,
          showTotal: (total) => `共 ${total} 条标准`,
          showSizeChanger: true,
          pageSizeOptions: ['10', '20', '50', '100'],
          onChange: (page, pageSize) => onPageChange?.(page, pageSize),
        }}
      />

      <Modal
        title="标准详情"
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setSummary(''); }}
        footer={null}
        width={700}
      >
        {detailLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
        ) : detail ? (
          <>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="标准号" span={2}>
                {detail.standard_number}
                {detail.hcno && (
                  <a
                    href={`https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=${detail.hcno}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ marginLeft: 12 }}
                  >
                    <LinkOutlined /> 官网查看
                  </a>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="中文名称" span={2}>{detail.cn_name}</Descriptions.Item>
              {detail.en_name && (
                <Descriptions.Item label="英文名称" span={2}>{detail.en_name}</Descriptions.Item>
              )}
              <Descriptions.Item label="状态">
                <Tag color={statusColorMap[detail.status] || 'default'}>{detail.status}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="类型">{detail.standard_type}</Descriptions.Item>
              <Descriptions.Item label="ICS 分类">{detail.ics_code || '-'}</Descriptions.Item>
              <Descriptions.Item label="CCS 分类">{detail.ccs_code || '-'}</Descriptions.Item>
              <Descriptions.Item label="发布日期">{detail.publish_date || '-'}</Descriptions.Item>
              <Descriptions.Item label="实施日期">{detail.implement_date || '-'}</Descriptions.Item>
              {detail.abolish_date && <Descriptions.Item label="废止日期">{detail.abolish_date}</Descriptions.Item>}
              {detail.replaced_by && <Descriptions.Item label="替代标准">{detail.replaced_by}</Descriptions.Item>}
            </Descriptions>

            <div style={{ marginTop: 16 }}>
              {!summary && !summaryLoading && (
                <Button
                  type="primary"
                  icon={<RobotOutlined />}
                  onClick={() => loadSummary(detail.id)}
                  block
                >
                  AI 智能解读此标准
                </Button>
              )}
              {summaryLoading && (
                <div style={{ textAlign: 'center', padding: 20 }}>
                  <Spin tip="AI 正在解读标准..." />
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
          <p>加载失败</p>
        )}
      </Modal>
    </>
  )
})
