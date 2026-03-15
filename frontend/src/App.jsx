import { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Spin } from 'antd'
import Layout from './components/Layout'

const HomePage = lazy(() => import('./pages/HomePage'))
const SearchPage = lazy(() => import('./pages/SearchPage'))
const CalendarPage = lazy(() => import('./pages/CalendarPage'))
const AIConfigPage = lazy(() => import('./pages/AIConfigPage'))

const PageLoader = (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 300 }}>
    <Spin size="large" />
  </div>
)

export default function App() {
  return (
    <Layout>
      <Suspense fallback={PageLoader}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/ai-config" element={<AIConfigPage />} />
        </Routes>
      </Suspense>
    </Layout>
  )
}
