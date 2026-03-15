import { Layout as AntLayout, Menu } from 'antd'
import { SearchOutlined, UnorderedListOutlined, HomeOutlined, SettingOutlined } from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'

const { Header, Content, Footer } = AntLayout

const menuItems = [
  { key: '/', icon: <HomeOutlined />, label: '首页' },
  { key: '/search', icon: <SearchOutlined />, label: '标准查询' },
  { key: '/calendar', icon: <UnorderedListOutlined />, label: '标准总览' },
  { key: '/ai-config', icon: <SettingOutlined />, label: 'AI 设置' },
]

export default function Layout({ children }) {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <AntLayout style={{ minHeight: '100vh', background: '#f7f8fa' }}>
      <Header style={{
        display: 'flex',
        alignItems: 'center',
        padding: '0 40px',
        background: '#fff',
        borderBottom: '1px solid #e5e6eb',
        height: 56,
        lineHeight: '56px',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        <div
          style={{
            color: '#1d2129',
            fontSize: 17,
            fontWeight: 700,
            marginRight: 48,
            cursor: 'pointer',
            letterSpacing: 0.5,
            whiteSpace: 'nowrap',
          }}
          onClick={() => navigate('/')}
        >
          GB 国标查询
        </div>
        <Menu
          mode="horizontal"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{
            flex: 1,
            borderBottom: 'none',
            background: 'transparent',
            fontSize: 14,
          }}
        />
      </Header>
      <Content className="app-content">
        {children}
      </Content>
      <Footer style={{
        textAlign: 'center',
        color: '#c9cdd4',
        background: '#f7f8fa',
        padding: '16px 40px',
        fontSize: 12,
      }}>
        数据来源: 国家标准委官网 (openstd.samr.gov.cn)
      </Footer>
    </AntLayout>
  )
}
