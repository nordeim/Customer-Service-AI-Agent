import React, { useEffect, useState } from 'react'

interface Intent {
  id: string
  name: string
  patterns: string[]
  responses: string[]
  active: boolean
}

const IntentManager: React.FC = () => {
  const [intents, setIntents] = useState<Intent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Minimal stub - replace with real API call
    setTimeout(() => {
      setIntents([{
        id: 'intent-1',
        name: 'greeting',
        patterns: ['hi', 'hello'],
        responses: ['Hey! How can I help you today?'],
        active: true
      }])
      setLoading(false)
    }, 200)
  }, [])

  if (loading) return <div className="p-6">Loading...</div>

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h2 className="text-2xl font-semibold mb-4">Intent Manager</h2>
      <div className="grid gap-4">
        {intents.map((it) => (
          <div key={it.id} className="border rounded-lg p-4 bg-white">
            <div className="flex justify-between items-center mb-2">
              <h3 className="font-medium">{it.name}</h3>
              <span className={`px-2 py-1 rounded ${it.active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-700'}`}>{it.active ? 'Active' : 'Inactive'}</span>
            </div>
            <p className="text-sm text-gray-600">Patterns: {it.patterns.join(', ')}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default IntentManager
