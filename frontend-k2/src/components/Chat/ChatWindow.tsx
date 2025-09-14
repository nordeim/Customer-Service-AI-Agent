import React, { useState, useCallback, useRef, useEffect } from 'react'
import { useChat, useTypingIndicator } from '@/hooks/useChat'
import { MessageList } from './MessageList'
import { MessageInput } from './MessageInput'
import { TypingIndicator } from './TypingIndicator'
import { Conversation, MessageContentType } from '@/types'
import { useAppSelector } from '@/store'
import { selectIsMobile } from '@/store/slices/uiSlice'
import { clsx } from 'clsx'

interface ChatWindowProps {
  conversation: Conversation
  className?: string
  onClose?: () => void
  onMinimize?: () => void
  onMaximize?: () => void
  showHeader?: boolean
  showFooter?: boolean
  autoScroll?: boolean
  enableTyping?: boolean
  enableFileUpload?: boolean
  maxFileSize?: number
  acceptedFileTypes?: string[]
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  conversation,
  className,
  onClose,
  onMinimize,
  onMaximize,
  showHeader = true,
  showFooter = true,
  autoScroll = true,
  enableTyping = true,
  enableFileUpload = true,
  maxFileSize = 10 * 1024 * 1024, // 10MB
  acceptedFileTypes = ['image/*', 'text/*', 'application/pdf'],
}) => {
  const isMobile = useAppSelector(selectIsMobile)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const [isAtBottom, setIsAtBottom] = useState(true)
  const [unreadCount, setUnreadCount] = useState(0)

  const {
    messages,
    currentConversation,
    isSending,
    isTyping,
    typingUsers,
    sendMessage,
    editMessage,
    deleteMessage,
    loadMoreMessages,
    markMessagesAsRead,
    addOptimisticMessage,
    scrollToBottom,
    scrollToMessage,
    error,
    clearError,
  } = useChat({
    conversationId: conversation.id,
    autoScroll,
    markAsReadOnVisible: true,
    enableTyping,
  })

  const { isTyping: localIsTyping, startTyping, stopTyping } = useTypingIndicator(
    conversation.id,
    enableTyping
  )

  // Monitor scroll position
  useEffect(() => {
    const container = scrollContainerRef.current
    if (!container) return

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container
      const atBottom = scrollHeight - scrollTop - clientHeight < 50
      setIsAtBottom(atBottom)
      
      // Load more messages when scrolling to top
      if (scrollTop < 100 && !isLoading) {
        loadMoreMessages()
      }
    }

    container.addEventListener('scroll', handleScroll)
    return () => container.removeEventListener('scroll', handleScroll)
  }, [loadMoreMessages])

  // Calculate unread messages when not at bottom
  useEffect(() => {
    if (isAtBottom) {
      setUnreadCount(0)
      return
    }

    const unreadMessages = messages.filter(message => 
      message.conversation_id === conversation.id &&
      message.sender_type !== 'user' &&
      !message.seen_at
    )

    setUnreadCount(unreadMessages.length)
  }, [messages, conversation.id, isAtBottom])

  const handleSendMessage = useCallback(async (
    content: string,
    contentType: MessageContentType = 'text',
    files?: File[]
  ) => {
    try {
      await sendMessage(content, contentType)
      
      // Handle file uploads if provided
      if (files && files.length > 0) {
        // File upload logic would be implemented here
        console.log('Files to upload:', files)
      }
      
      // Stop typing indicator
      stopTyping()
    } catch (error) {
      console.error('Failed to send message:', error)
    }
  }, [sendMessage, stopTyping])

  const handleMessageRetry = useCallback(async (messageId: string) => {
    const message = messages.find(m => m.id === messageId)
    if (message && message.failed_delivery) {
      // Retry sending the message
      await handleSendMessage(message.content, message.content_type as MessageContentType)
    }
  }, [messages, handleSendMessage])

  const handleScrollToBottom = useCallback(() => {
    scrollToBottom()
    setUnreadCount(0)
  }, [scrollToBottom])

  const handleInputFocus = useCallback(() => {
    startTyping()
  }, [startTyping])

  const handleInputBlur = useCallback(() => {
    stopTyping()
  }, [stopTyping])

  const handleInputChange = useCallback(() => {
    // Reset typing timeout
    startTyping()
  }, [startTyping])

  const handleLoadEarlier = useCallback(async () => {
    if (!isLoading && hasMoreMessages) {
      await loadMoreMessages()
    }
  }, [isLoading, hasMoreMessages, loadMoreMessages])

  const isLoading = !currentConversation || messages.length === 0

  return (
    <div className={clsx(
      'flex flex-col h-full bg-white dark:bg-gray-900 rounded-lg shadow-lg',
      'border border-gray-200 dark:border-gray-700',
      className
    )}>
      {/* Header */}
      {showHeader && (
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <div className="w-10 h-10 bg-primary-500 rounded-full flex items-center justify-center">
                <span className="text-white font-medium">
                  {conversation.title?.charAt(0).toUpperCase() || 'C'}
                </span>
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white truncate">
                {conversation.title || 'Conversation'}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {conversation.status === 'active' ? 'Active' : 'Inactive'}
                {typingUsers.length > 0 && (
                  <span className="ml-1">
                    • Someone is typing...
                  </span>
                )}
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            {onMinimize && (
              <button
                onClick={onMinimize}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
                aria-label="Minimize chat"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                </svg>
              </button>
            )}
            
            {onMaximize && (
              <button
                onClick={onMaximize}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
                aria-label="Maximize chat"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                </svg>
              </button>
            )}
            
            {onClose && (
              <button
                onClick={onClose}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
                aria-label="Close chat"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800">
          <div className="flex items-center justify-between">
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            <button
              onClick={clearError}
              className="text-red-400 hover:text-red-600 dark:hover:text-red-300"
              aria-label="Clear error"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Messages Container */}
      <div className="flex-1 overflow-hidden">
        <div 
          ref={scrollContainerRef}
          className="h-full overflow-y-auto overflow-x-hidden"
          role="log"
          aria-live="polite"
          aria-label="Chat messages"
        >
          {/* Load Earlier Messages */}
          {hasMoreMessages && (
            <div className="p-4 text-center">
              <button
                onClick={handleLoadEarlier}
                disabled={isLoading}
                className={clsx(
                  'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
                  'bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700',
                  'text-gray-700 dark:text-gray-300',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
                )}
              >
                {isLoading ? 'Loading...' : 'Load earlier messages'}
              </button>
            </div>
          )}

          {/* Messages List */}
          <MessageList
            messages={messages}
            conversation={conversation}
            onMessageEdit={editMessage}
            onMessageDelete={deleteMessage}
            onMessageRetry={handleMessageRetry}
            onScrollToMessage={scrollToMessage}
          />

          {/* Typing Indicator */}
          {typingUsers.length > 0 && (
            <TypingIndicator 
              typingUsers={typingUsers}
              className="p-4"
            />
          )}
        </div>
      </div>

      {/* Unread Messages Indicator */}
      {!isAtBottom && unreadCount > 0 && (
        <button
          onClick={handleScrollToBottom}
          className={clsx(
            'absolute bottom-20 left-1/2 transform -translate-x-1/2',
            'px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white',
            'rounded-full shadow-lg transition-all duration-200',
            'flex items-center space-x-2 text-sm font-medium'
          )}
          aria-label={`Scroll to bottom - ${unreadCount} unread messages`}
        >
          <span>{unreadCount} new message{unreadCount !== 1 ? 's' : ''}</span>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
          </svg>
        </button>
      )}

      {/* Footer / Input Area */}
      {showFooter && (
        <div className="border-t border-gray-200 dark:border-gray-700 p-4">
          <MessageInput
            conversationId={conversation.id}
            onSendMessage={handleSendMessage}
            onFocus={handleInputFocus}
            onBlur={handleInputBlur}
            onChange={handleInputChange}
            disabled={isSending || conversation.status === 'resolved'}
            enableFileUpload={enableFileUpload}
            maxFileSize={maxFileSize}
            acceptedFileTypes={acceptedFileTypes}
            placeholder={isTyping ? 'Someone is typing...' : 'Type your message...'}
            aria-label="Message input"
          />
          
          {/* Typing Status */}
          {localIsTyping && (
            <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              Typing...
            </div>
          )}
        </div>
      )}
    </div>
  )
}

ChatWindow.displayName = 'ChatWindow'
