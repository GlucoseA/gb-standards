import { useState, useEffect } from 'react'
import { Form, Input, Button, message, Alert } from 'antd'
import { KeyOutlined, ApiOutlined, RobotOutlined, CheckCircleOutlined, ExperimentOutlined } from '@ant-design/icons'
import { testAIConnection } from '../api/client'

const STORAGE_KEY = 'gb_ai_config'

function loadSavedConfig() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function getAIHeaders() {
  const cfg = loadSavedConfig()
  if (!cfg?.api_key) return {}
  const headers = { 'X-AI-API-Key': cfg.api_key }
  if (cfg.api_url) headers['X-AI-API-URL'] = cfg.api_url
  if (cfg.model) headers['X-AI-Model'] = cfg.model
  return headers
}

export default function AIConfigPage() {
  const [form] = Form.useForm()
  const [saved, setSaved] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)

  useEffect(() => {
    const cfg = loadSavedConfig()
    if (cfg) {
      form.setFieldsValue({
        api_url: cfg.api_url || '',
        api_key: cfg.api_key || '',
        model: cfg.model || '',
      })
      setSaved(true)
    }
  }, [])

  const handleSave = (values) => {
    const config = {
      api_url: values.api_url?.trim() || '',
      api_key: values.api_key?.trim() || '',
      model: values.model?.trim() || '',
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
    setSaved(true)
    setTestResult(null)
    message.success('配置已保存')
  }

  const handleClear = () => {
    localStorage.removeItem(STORAGE_KEY)
    form.resetFields()
    setSaved(false)
    setTestResult(null)
    message.info('配置已清除')
  }

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    const res = await testAIConnection()
    setTestResult(res)
    setTesting(false)
  }

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: 'calc(100vh - 56px - 52px)',
      padding: '40px 20px',
    }}>
      <div style={{
        width: '100%',
        maxWidth: 420,
        background: '#fff',
        borderRadius: 16,
        boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
        padding: '40px 36px 32px',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{
            width: 56,
            height: 56,
            borderRadius: 16,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px',
          }}>
            <RobotOutlined style={{ fontSize: 28, color: '#fff' }} />
          </div>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: '#1d2129', marginBottom: 4 }}>
            LLM API 设定
          </h2>
          <p style={{ fontSize: 13, color: '#86909c', margin: 0 }}>
            配置大语言模型接口，启用标准智能解读
          </p>
        </div>

        {saved && (
          <Alert
            message="配置已保存"
            type="success"
            showIcon
            icon={<CheckCircleOutlined />}
            style={{ marginBottom: 20, borderRadius: 8 }}
          />
        )}

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          requiredMark={false}
          initialValues={{
            api_url: 'https://api.deepseek.com/chat/completions',
            model: 'deepseek-chat',
          }}
        >
          <Form.Item
            label="API 地址"
            name="api_url"
            rules={[{ required: true, message: '请输入 API 地址' }]}
          >
            <Input
              prefix={<ApiOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="https://api.deepseek.com/chat/completions"
              size="large"
              style={{ borderRadius: 8 }}
            />
          </Form.Item>

          <Form.Item
            label="API Key"
            name="api_key"
            rules={[{ required: true, message: '请输入 API Key' }]}
          >
            <Input.Password
              prefix={<KeyOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="sk-..."
              size="large"
              style={{ borderRadius: 8 }}
            />
          </Form.Item>

          <Form.Item
            label="模型"
            name="model"
            rules={[{ required: true, message: '请输入模型名称' }]}
          >
            <Input
              prefix={<RobotOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="deepseek-chat"
              size="large"
              style={{ borderRadius: 8 }}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 12 }}>
            <Button
              type="primary"
              htmlType="submit"
              block
              size="large"
              style={{
                borderRadius: 8,
                height: 44,
                fontWeight: 600,
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                border: 'none',
              }}
            >
              保存配置
            </Button>
          </Form.Item>

          <div style={{ display: 'flex', gap: 8 }}>
            <Button
              icon={<ExperimentOutlined />}
              onClick={handleTest}
              loading={testing}
              disabled={!saved}
              block
              size="large"
              style={{ borderRadius: 8, height: 40 }}
            >
              测试连接
            </Button>
            <Button
              onClick={handleClear}
              disabled={!saved}
              block
              size="large"
              style={{ borderRadius: 8, height: 40 }}
            >
              清除配置
            </Button>
          </div>
        </Form>

        {testResult && (
          <Alert
            message={testResult.success ? '连接成功' : '连接失败'}
            description={testResult.message}
            type={testResult.success ? 'success' : 'error'}
            showIcon
            style={{ marginTop: 16, borderRadius: 8 }}
          />
        )}

        <p style={{
          fontSize: 12,
          color: '#c9cdd4',
          textAlign: 'center',
          marginTop: 20,
          marginBottom: 0,
          lineHeight: 1.6,
        }}>
          支持 OpenAI 兼容接口：DeepSeek、OpenAI、Ollama 等<br />
          配置保存在浏览器本地，不会上传到服务器
        </p>
      </div>
    </div>
  )
}
