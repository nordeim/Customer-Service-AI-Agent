import React, { useCallback, useMemo } from 'react'
import { Message, Conversation, MessageContentType } from '@/types'
import { format, isToday, isYesterday, formatDistanceToNow } from 'date-fns'
import { clsx } from 'clsx'

interface MessageListProps {
  messages: Message[]
  conversation: Conversation
  onMessageEdit: (messageId: string, newContent: string) => Promise<void>
  onMessageDelete: (messageId: string) => Promise<void>
  onMessageRetry: (messageId: string) => Promise<void>
  onScrollToMessage: (messageId: string) => void
  className?: string
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  conversation,
  onMessageEdit,
  onMessageDelete,
  onMessageRetry,
  onScrollToMessage,
  className,
}) => {
  // Group messages by date
  const groupedMessages = useMemo(() => {
    const groups: Record<string, Message[]> = {}
    
    messages.forEach(message => {
      const date = new Date(message.created_at)
      const dateKey = format(date, 'yyyy-MM-dd')
      
      if (!groups[dateKey]) {
        groups[dateKey] = []
      }
      groups[dateKey].push(message)
    })
    
    return groups
  }, [messages])

  const formatMessageTime = useCallback((timestamp: string): string => {
    const date = new Date(timestamp)
    const now = new Date()
    
    if (isToday(date)) {
      return format(date, 'h:mm a')
    } else if (isYesterday(date)) {
      return `Yesterday ${format(date, 'h:mm a')}`
    } else if (date.getFullYear() === now.getFullYear()) {
      return format(date, 'MMM d, h:mm a')
    } else {
      return format(date, 'MMM d, yyyy, h:mm a')
    }
  }, [])

  const formatDateSeparator = useCallback((dateKey: string): string => {
    const date = new Date(dateKey)
    const now = new Date()
    
    if (isToday(date)) {
      return 'Today'
    } else if (isYesterday(date)) {
      return 'Yesterday'
    } else {
      return format(date, 'EEEE, MMMM d, yyyy')
    }
  }, [])

  const isMessageFromCurrentUser = useCallback((message: Message): boolean => {
    return message.sender_type === 'user'
  }, [])

  const getMessageStatus = useCallback((message: Message): 'sending' | 'sent' | 'delivered' | 'failed' => {
    if (message.failed_delivery) return 'failed'
    if (message.id.startsWith('optimistic-')) return 'sending'
    if (message.seen_at) return 'delivered'
    return 'sent'
  }, [])

  const renderMessageContent = useCallback((message: Message): React.ReactNode => {
    const { content, content_type, content_html, content_markdown } = message
    
    switch (content_type) {
      case 'html':
        return (
          <div 
            dangerouslySetInnerHTML={{ __html: content_html || content }} 
            className="prose prose-sm dark:prose-invert max-w-none"
          />
        )
      case 'markdown':
        return (
          <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">
            {content_markdown || content}
          </div>
        )
      case 'code':
        return (
          <pre className="bg-gray-100 dark:bg-gray-800 p-3 rounded-lg overflow-x-auto text-sm">
            <code>{content}</code>
          </pre>
        )
      default:
        return (
          <div className="whitespace-pre-wrap break-words">
            {content}
          </div>
        )
    }
  }, [])

  const renderMessageAttachments = useCallback((message: Message): React.ReactNode => {
    if (!message.has_attachments || !message.attachments.length) return null
    
    return (
      <div className="mt-2 space-y-2">
        {message.attachments.map((attachment, index) => (
          <div
            key={index}
            className="inline-flex items-center space-x-2 p-2 bg-gray-100 dark:bg-gray-800 rounded-lg"
          >
            {attachment.type?.startsWith('image/') ? (
              <img
                src={attachment.url}
                alt={attachment.name}
                className="max-w-xs max-h-48 rounded-lg object-cover"
                loading="lazy"
              />
            ) : (
              <a
                href={attachment.url}
                download={attachment.name}
                className="flex items-center space-x-2 text-primary-600 dark:text-primary-400 hover:underline"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                </svg>
                <span className="text-sm">{attachment.name}</span>
              </a>
            )}
          </div>
        ))}
      </div>
    )
  }, [])

  const renderMessageStatus = useCallback((message: Message): React.ReactNode => {
    const status = getMessageStatus(message)
    
    switch (status) {
      case 'sending':
        return (
          <div className="flex items-center space-x-1 text-gray-400 dark:text-gray-500">
            <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span className="text-xs">Sending...</span>
          </div>
        )
      case 'failed':
        return (
          <div className="flex items-center space-x-1">
            <button
              onClick={() => onMessageRetry(message.id)}
              className="flex items-center space-x-1 text-red-500 hover:text-red-600 text-xs"
              aria-label="Retry sending message"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <span>Failed - Retry?</span>
            </button>
          </div>
        )
      case 'delivered':
        return (
          <svg className="w-3 h-3 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        )
      default:
        return (
          <svg className="w-3 h-3 text-gray-400 dark:text-gray-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        )
    }
  }, [getMessageStatus, onMessageRetry])

  const renderQuickReplies = useCallback((message: Message): React.ReactNode => {
    if (!message.quick_replies || !message.quick_replies.length) return null
    
    return (
      <div className="mt-3 flex flex-wrap gap-2">
        {message.quick_replies.map((reply, index) => (
          <button
            key={index}
            onClick={() => {
              // Handle quick reply click
              console.log('Quick reply clicked:', reply)
            }}
            className="px-3 py-1 text-sm bg-primary-100 hover:bg-primary-200 dark:bg-primary-900 dark:hover:bg-primary-800 text-primary-700 dark:text-primary-300 rounded-full transition-colors"
          >
            {reply.text || reply.title}
          </button>
        ))}
      </div>
    )
  }, [])

  return (
    <div className={clsx('space-y-4', className)} role="log" aria-label="Chat messages">
      {Object.entries(groupedMessages).map(([dateKey, dayMessages]) => (
        <div key={dateKey}>
          {/* Date Separator */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300 dark:border-gray-600" />
            </div>
            <div className="relative flex justify-center">
              <span className="px-3 bg-white dark:bg-gray-900 text-sm text-gray-500 dark:text-gray-400 font-medium">
                {formatDateSeparator(dateKey)}
              </span>
            </div>
          </div>

          {/* Messages for this date */}
          <div className="space-y-4">
            {dayMessages.map((message) => {
              const isCurrentUser = isMessageFromCurrentUser(message)
              const messageStatus = getMessageStatus(message)

              return (
                <div
                  key={message.id}
                  data-message-id={message.id}
                  className={clsx(
                    'flex',
                    isCurrentUser ? 'justify-end' : 'justify-start',
                    message.failed_delivery && 'opacity-75'
                  )}
                >
                  <div
                    className={clsx(
                      'max-w-[70%] lg:max-w-[60%] rounded-lg px-4 py-2',
                      'shadow-sm',
                      isCurrentUser
                        ? 'bg-primary-500 text-white'
                        : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100'
                    )}
                  >
                    {/* Message Content */}
                    <div className="text-sm">
                      {renderMessageContent(message)}
                    </div>

                    {/* Attachments */}
                    {renderMessageAttachments(message)}

                    {/* Quick Replies */}
                    {!isCurrentUser && renderQuickReplies(message)}

                    {/* Message Metadata */}
                    <div className={clsx(
                      'flex items-center justify-between mt-2',
                      'text-xs',
                      isCurrentUser ? 'text-primary-100' : 'text-gray-500 dark:text-gray-400'
                    )}>
                      <time 
                        dateTime={message.created_at}
                        className="flex-shrink-0"
                        title={new Date(message.created_at).toLocaleString()}
                      >
                        {formatMessageTime(message.created_at)}
                      </time>
                      
                      {isCurrentUser && (
                        <div className="flex items-center space-x-1 ml-2">
                          {renderMessageStatus(message)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ))}

      {messages.length === 0 && (
        <div className="text-center py-12">
          <div className="text-gray-500 dark:text-gray-400">
            <svg className="w-12 h-12 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p className="text-sm">No messages yet. Start the conversation!</p>
          </div>
        </div>
      )}
    </div>
  )
}

MessageList.displayName = 'MessageList'
