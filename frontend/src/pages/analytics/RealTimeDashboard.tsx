import React, { useEffect, useState } from 'react'

interface AnalyticsData {
  deflectionRate: number
  csat: number
  activeConversations: number
  avgResponseTime: number
  escalationRate: number
}

const RealTimeDashboard: React.FC = () => {
  const [analytics, setAnalytics] = useState<AnalyticsData>({ deflectionRate: 0.24, csat: 4.3, activeConversations: 12, avgResponseTime: 320, escalationRate: 0.06 })

  useEffect(() => {
    // placeholder for websocket connection
    const t = setInterval(() => {
      setAnalytics((a) => ({ ...a, activeConversations: Math.max(0, a.activeConversations + (Math.random() > 0.5 ? 1 : -1)) }))
    }, 2000)
    return () => clearInterval(t)
  }, [])

  const MetricCard = ({ title, value, unit }: { title: string; value: number | string; unit?: string }) => (
    <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
      <h3 className="text-sm font-medium text-gray-500">{title}</h3>
      <p className="text-2xl font-bold mt-1">{value}{unit || ''}</p>
    </div>
  )

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Real-time Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard title="Deflection Rate" value={`${Math.round(analytics.deflectionRate * 100)}%`} />
        <MetricCard title="CSAT" value={`${analytics.csat.toFixed(1)}/5.0`} />
        <MetricCard title="Active Conversations" value={analytics.activeConversations} />
        <MetricCard title="Avg Response Time" value={`${Math.round(analytics.avgResponseTime)} ms`} />
        <MetricCard title="Escalation Rate" value={`${Math.round(analytics.escalationRate * 100)}%`} />
      </div>
    </div>
  )
}

export default RealTimeDashboard
