import React from 'react'

interface MessageBubbleProps {
  content: string
  isUser?: boolean
  emotion?: 'angry' | 'happy' | 'neutral' | 'excited'
  timestamp?: string
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ content, isUser = false, emotion = 'neutral', timestamp }) => {
  const base = 'p-3 rounded-lg max-w-xs lg:max-w-md mb-2'
  const userClass = 'bg-blue-500 text-white self-end'
  const botClass = `text-gray-800 self-start border ${
    emotion === 'angry' ? 'border-emotion-angry bg-red-50' :
    emotion === 'happy' ? 'border-emotion-happy bg-green-50' :
    emotion === 'excited' ? 'border-emotion-excited bg-yellow-50' :
    'border-gray-300 bg-white'
  }`

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`${base} ${isUser ? userClass : botClass}`}>
        <p className="text-sm whitespace-pre-wrap">{content}</p>
        {timestamp && (
          <p className="text-xs text-right mt-1 opacity-70">{new Date(timestamp).toLocaleTimeString()}</p>
        )}
      </div>
    </div>
  )
}

export default MessageBubble
