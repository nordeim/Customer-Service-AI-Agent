import React, { useState } from 'react'

interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
}

const ChatInput: React.FC<ChatInputProps> = ({ onSend, disabled = false }) => {
  const [value, setValue] = useState('')

  const submit = (e?: React.FormEvent) => {
    e?.preventDefault()
    const trimmed = value.trim()
    if (trimmed && !disabled) {
      onSend(trimmed)
      setValue('')
    }
  }

  return (
    <form onSubmit={submit} className="flex gap-2 p-4 border-t bg-white">
      <input
        aria-label="Chat input field"
        placeholder="Type your message..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="flex-1 p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        disabled={disabled}
      />
      <button
        type="submit"
        disabled={!value.trim() || disabled}
        className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
        aria-label="Send message"
      >
        Send
      </button>
    </form>
  )
}

export default ChatInput
