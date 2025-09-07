import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import ChatPage from './pages/chat/ChatPage'
import IntentManager from './pages/admin/IntentManager'
import RealTimeDashboard from './pages/analytics/RealTimeDashboard'

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<ChatPage />} />
        <Route path="/admin" element={<IntentManager />} />
        <Route path="/analytics" element={<RealTimeDashboard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  )
}

export default App
