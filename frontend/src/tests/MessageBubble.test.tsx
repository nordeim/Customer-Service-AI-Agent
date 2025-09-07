import React from 'react'
import { render, screen } from '@testing-library/react'
import MessageBubble from '../components/chat/MessageBubble'

describe('MessageBubble', () => {
  it('renders content and timestamp', () => {
    const ts = '2023-10-01T12:00:00Z'
    render(<MessageBubble content="Hello world" timestamp={ts} />)
    expect(screen.getByText('Hello world')).toBeInTheDocument()
    // timestamp should render localized time string
    expect(screen.getByText(/12:00/)).toBeInTheDocument()
  })

  it('applies user classes when isUser is true', () => {
    render(<MessageBubble content="u" isUser={true} />)
    const el = screen.getByText('u').closest('div')
    expect(el).toHaveClass('bg-blue-500')
  })
})
