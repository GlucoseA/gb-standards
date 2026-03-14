import { useState, useEffect } from 'react'
import { Card, Form, Input, Button, message, Alert, Spin, Descriptions, Tag, Divider, Progress } from 'antd'
import {
  ApiOutlined, KeyOutlined, RobotOutlined, CheckCircleOutlined,
  ExperimentOutlined, DatabaseOutlined, BuildOutlined,
} from '@ant-design/icons'
import { getAIConfig, updateAIConfig, testAIConfig, getVectorStatus, buildVectorIndex } from '../api/client'

export default function SettingsPage() {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [config, setConfig] = useState(null)

  // 向量索引
  const [vectorStatus, setVectorStatus] = useState(null)
  const [building, setBuilding] = useState(false)

  useEffect(() => {
    loadConfig()
    loadVectorStatus()
  }, [])

  // 构建中轮询
  useEffect(() => {
    if (!building) return
    const interval = setInterval(async () => {
      const s = await getVectorStatus()
      setVectorStatus(s)
      if (!s.is_building) {
        setBuilding(false)
        message.success(s.message || '索引构建完成')
      }
    }, 3000)
    return () => clearInterval(interval)
  }, [building])

  const loadConfig = async () => {
    setLoading(true)
    try {
      const cfg = await getAIConfig()
      setConfig(cfg)
      form.setFieldsValue({
        api_url: cfg.api_url,
        model: cfg.model,
        api_key: '',  // 不回显密钥
      })
    } catch {
      message.error('加载配置失败')
    }
    setLoading(false)
  }

  const loadVectorStatus = async () => {
    try {
      const s = await getVectorStatus()
      setVectorStatus(s)
      if (s.is_building) setBuilding(true)
    } catch { /* ignore */ }
  }

  const handleSave = async (values) => {
    setSaving(true)
    setTestResult(null)
    try {
      const payload = {}
      if (values.api_url) payload.api_url = values.api_url
      if (values.api_key) payload.api_key = values.api_key
      if (values.model) payload.model = values.model
      const result = await updateAIConfig(payload)
      setConfig(result)
      form.setFieldsValue({ api_key: '' })
      message.success('配置已保存')
    } catch {
      message.error('保存失败')
    }
    setSaving(false)
  }

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const result = await testAIConfig()
      setTestResult(result)
    } catch {
      setTestResult({ success: false, message: '请求失败，请检查网络连接' })
    }
    setTesting(false)
  }

  const handleBuildIndex = async () => {
    setBuilding(true)
    try {
      await buildVectorIndex()
      message.info('索引构建已启动')
      loadVectorStatus()
    } catch {
      message.error('启动失败')
      setBuilding(false)
    }
  }

  if (loading) {
    return (
      <div className="page-container" style={{ textAlign: 'center', paddingTop: 80 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div className="page-container" style={{ maxWidth: 800 }}>
      <h2 className="section-title"><RobotOutlined /> AI 设置</h2>

      {/* AI 接口配置 */}
      <Card
        title={<><ApiOutlined /> LLM 接口配置</>}
        style={{ marginBottom: 24 }}
      >
        <p style={{ color: '#86909c', fontSize: 13, marginBottom: 16 }}>
          配置兼容 OpenAI 协议的大语言模型接口，用于 AI 智能解读功能。支持 DeepSeek、OpenAI、本地 Ollama 等。
        </p>

        {config?.has_key && (
          <Alert
            message={<>当前密钥: <code>{config.api_key_masked}</code></>}
            type="success"
            showIcon
            icon={<CheckCircleOutlined />}
            style={{ marginBottom: 16 }}
          />
        )}

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          requiredMark={false}
        >
          <Form.Item
            label="API 地址"
            name="api_url"
            rules={[{ required: true, message: '请输入 API 地址' }]}
            extra="如: https://api.deepseek.com/chat/completions 或 http://localhost:11434/v1/chat/completions"
          >
            <Input prefix={<ApiOutlined />} placeholder="https://api.deepseek.com/chat/completions" size="large" />
          </Form.Item>

          <Form.Item
            label="API Key"
            name="api_key"
            extra={config?.has_key ? '已有密钥，留空则保持不变' : '必填，用于鉴权'}
          >
            <Input.Password
              prefix={<KeyOutlined />}
              placeholder={config?.has_key ? '留空保持当前密钥不变' : '请输入 API Key'}
              size="large"
            />
          </Form.Item>

          <Form.Item
            label="模型名称"
            name="model"
            rules={[{ required: true, message: '请输入模型名称' }]}
            extra="如: deepseek-chat, gpt-4o, qwen-plus"
          >
            <Input prefix={<RobotOutlined />} placeholder="deepseek-chat" size="large" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <div style={{ display: 'flex', gap: 12 }}>
              <Button type="primary" htmlType="submit" loading={saving} size="large">
                保存配置
              </Button>
              <Button
                icon={<ExperimentOutlined />}
                onClick={handleTest}
                loading={testing}
                disabled={!config?.has_key}
                size="large"
              >
                测试连接
              </Button>
            </div>
          </Form.Item>
        </Form>

        {testResult && (
          <Alert
            message={testResult.success ? '连接成功' : '连接失败'}
            description={testResult.message}
            type={testResult.success ? 'success' : 'error'}
            showIcon
            style={{ marginTop: 16 }}
          />
        )}
      </Card>

      {/* 向量索引管理 */}
      <Card
        title={<><DatabaseOutlined /> 语义搜索索引</>}
      >
        <p style={{ color: '#86909c', fontSize: 13, marginBottom: 16 }}>
          构建语义向量索引后，搜索框将支持语义搜索。例如输入"给手机充电的电池"可匹配到"便携式锂离子电池和电池组"。
        </p>

        {vectorStatus && (
          <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
            <Descriptions.Item label="索引状态">
              {vectorStatus.exists
                ? <Tag color="green">已构建</Tag>
                : <Tag color="default">未构建</Tag>
              }
            </Descriptions.Item>
            <Descriptions.Item label="索引条数">
              {vectorStatus.count > 0 ? `${vectorStatus.count} 条标准` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="模型" span={2}>
              <code style={{ fontSize: 12 }}>{vectorStatus.model}</code>
            </Descriptions.Item>
            {vectorStatus.built_at && (
              <Descriptions.Item label="构建时间" span={2}>
                {new Date(vectorStatus.built_at).toLocaleString('zh-CN')}
              </Descriptions.Item>
            )}
          </Descriptions>
        )}

        {building && vectorStatus?.message && (
          <Alert
            message={vectorStatus.message}
            type="info"
            showIcon
            icon={<Spin size="small" />}
            style={{ marginBottom: 16 }}
          />
        )}

        <Button
          type="primary"
          icon={<BuildOutlined />}
          onClick={handleBuildIndex}
          loading={building}
          size="large"
        >
          {vectorStatus?.exists ? '重新构建索引' : '构建语义索引'}
        </Button>

        <p style={{ color: '#c9cdd4', fontSize: 12, marginTop: 12 }}>
          首次构建需要下载模型（约 480MB），后续构建约需 1-3 分钟。
        </p>
      </Card>
    </div>
  )
}
