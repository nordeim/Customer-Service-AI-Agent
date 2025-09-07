export const apiBase = import.meta.env.VITE_API_BASE || '/api/v1'

export async function sendMessage(conversationId: string | null, message: string) {
  const url = conversationId ? `${apiBase}/conversations/${conversationId}/messages` : `${apiBase}/conversations`
  const body = conversationId ? { content: message } : { initial_message: message }

  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error: ${res.status} ${text}`)
  }

  return res.json()
}
