import React, { useState } from 'react'
import MessageBubble from '../../components/chat/MessageBubble'
import ChatInput from '../../components/chat/ChatInput'
import { sendMessage } from '../../services/api'

interface Message {
  id: string
  content: string
  sender: 'user' | 'bot'
  timestamp: string
  emotion?: 'angry' | 'happy' | 'neutral' | 'excited'
}

const ChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    { id: 'welcome', content: 'Welcome to Salesforce AI Agent', sender: 'bot', timestamp: new Date().toISOString(), emotion: 'happy' }
  ])

  const send = async (text: string) => {
    const userMsg: Message = { id: `u-${Date.now()}`, content: text, sender: 'user', timestamp: new Date().toISOString() }
    setMessages((m) => [...m, userMsg])
    try {
      // attempt to call backend API
      const res = await sendMessage(null, text)
      // Expected res shape: { conversation_id, message: { id, content, sender, timestamp, emotion } }
      const bot = res?.message
      if (bot) {
        setMessages((m) => [...m, bot])
      } else {
        // fallback mock
        setMessages((m) => [...m, { id: `b-${Date.now()}`, content: 'Thanks — looking into that for you.', sender: 'bot', timestamp: new Date().toISOString(), emotion: 'neutral' }])
      }
    } catch (err) {
      // graceful degradation to mock response
      setMessages((m) => [...m, { id: `b-${Date.now()}`, content: 'Thanks — looking into that for you. (offline)', sender: 'bot', timestamp: new Date().toISOString(), emotion: 'neutral' }])
      console.error('sendMessage failed', err)
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white shadow p-4">
        <h1 className="text-xl font-semibold">Customer Service AI</h1>
      </header>

      <main className="flex-1 p-4 max-w-3xl mx-auto w-full flex flex-col">
        <div className="flex-1 overflow-auto mb-4 flex flex-col">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} content={msg.content} isUser={msg.sender === 'user'} emotion={msg.emotion} timestamp={msg.timestamp} />
          ))}
        </div>

        <ChatInput onSend={send} />
      </main>

      <footer className="text-center text-xs p-2 text-gray-500">v0.1.0</footer>
    </div>
  )
}

export default ChatPage
