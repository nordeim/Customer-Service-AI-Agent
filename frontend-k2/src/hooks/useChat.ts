import { useState, useCallback, useEffect, useRef } from 'react'
import { useAppDispatch, useAppSelector } from '@/store'
import { 
  sendMessage, 
  fetchMessages, 
  updateMessage,
  deleteMessage,
  markAsRead,
  setCurrentConversation,
  addMessage,
  optimisticMessage,
  removeOptimisticMessage,
  selectCurrentConversation,
  selectMessages,
  selectIsSending,
  selectIsTyping,
  selectTypingUsers 
} from '@/store/slices/conversationSlice'
import { 
  Message, 
  SendMessageData, 
  Conversation,
  MessageContentType,
  ConversationStatus 
} from '@/types'
import wsManager from '@/services/websocket'
import { v4 as uuidv4 } from 'uuid'

interface UseChatOptions {
  conversationId?: string;
  autoScroll?: boolean;
  markAsReadOnVisible?: boolean;
  enableTyping?: boolean;
  typingDelay?: number;
}

interface UseChatReturn {
  // State
  messages: Message[];
  currentConversation: Conversation | undefined;
  isSending: boolean;
  isTyping: boolean;
  typingUsers: Array<{
    user_id?: string;
    user_name?: string;
    is_typing: boolean;
    timestamp: string;
  }>;
  
  // Actions
  sendMessage: (content: string, contentType?: MessageContentType) => Promise<void>;
  editMessage: (messageId: string, newContent: string) => Promise<void>;
  deleteMessage: (messageId: string) => Promise<void>;
  loadMoreMessages: () => Promise<void>;
  markMessagesAsRead: (messageIds: string[]) => Promise<void>;
  setCurrentConversation: (conversation: Conversation | undefined) => void;
  
  // Typing
  startTyping: () => void;
  stopTyping: () => void;
  
  // Optimistic updates
  addOptimisticMessage: (content: string) => Message;
  
  // UI helpers
  scrollToBottom: () => void;
  scrollToMessage: (messageId: string) => void;
  
  // Error handling
  error: string | null;
  clearError: () => void;
}

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const {
    conversationId,
    autoScroll = true,
    markAsReadOnVisible = true,
    enableTyping = true,
    typingDelay = 1000,
  } = options

  const dispatch = useAppDispatch()
  const messages = useAppSelector(selectMessages)
  const currentConversation = useAppSelector(selectCurrentConversation)
  const isSending = useAppSelector(selectIsSending)
  const isTyping = useAppSelector(selectIsTyping)
  const typingUsers = useAppSelector(selectTypingUsers)
  const [error, setError] = useState<string | null>(null)
  
  // Refs for managing side effects
  const scrollContainerRef = useRef<HTMLDivElement | null>(null)
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const intersectionObserverRef = useRef<IntersectionObserver | null>(null)
  const lastReadMessageRef = useRef<string | null>(null)

  // Initialize conversation if ID provided
  useEffect(() => {
    if (conversationId && (!currentConversation || currentConversation.id !== conversationId)) {
      dispatch(fetchConversation(conversationId))
    }
  }, [conversationId, dispatch, currentConversation])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (autoScroll && messages.length > 0) {
      scrollToBottom()
    }
  }, [messages.length, autoScroll])

  // Setup WebSocket listeners for real-time updates
  useEffect(() => {
    if (currentConversation?.id) {
      // Join conversation room
      wsManager.joinConversation(currentConversation.id)
      
      // Setup typing indicators
      if (enableTyping) {
        wsManager.requestNotificationPermission()
      }
    }

    return () => {
      if (currentConversation?.id) {
        wsManager.leaveConversation(currentConversation.id)
      }
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current)
      }
      if (intersectionObserverRef.current) {
        intersectionObserverRef.current.disconnect()
      }
    }
  }, [currentConversation?.id, enableTyping])

  // Setup intersection observer for marking messages as read
  useEffect(() => {
    if (!markAsReadOnVisible || !currentConversation?.id) return

    intersectionObserverRef.current = new IntersectionObserver(
      (entries) => {
        const visibleMessages = entries
          .filter(entry => entry.isIntersecting)
          .map(entry => entry.target.getAttribute('data-message-id'))
          .filter(Boolean) as string[]

        if (visibleMessages.length > 0) {
          markMessagesAsRead(visibleMessages)
        }
      },
      {
        threshold: 0.5, // Message is 50% visible
        rootMargin: '0px 0px -100px 0px', // Account for input area
      }
    )

    return () => {
      if (intersectionObserverRef.current) {
        intersectionObserverRef.current.disconnect()
      }
    }
  }, [markAsReadOnVisible, currentConversation?.id])

  // Observe messages for read receipts
  useEffect(() => {
    if (!intersectionObserverRef.current) return

    // Clear previous observations
    intersectionObserverRef.current.disconnect()

    // Observe all unread messages from other users
    const unreadMessages = messages.filter(
      msg => 
        msg.conversation_id === currentConversation?.id &&
        msg.sender_type !== 'user' && 
        !msg.seen_at &&
        msg.id !== lastReadMessageRef.current
    )

    unreadMessages.forEach(message => {
      const element = document.querySelector(`[data-message-id="${message.id}"]`)
      if (element) {
        intersectionObserverRef.current?.observe(element)
      }
    })
  }, [messages, currentConversation?.id])

  const handleSendMessage = useCallback(async (
    content: string, 
    contentType: MessageContentType = 'text'
  ): Promise<void> => {
    if (!currentConversation?.id || !content.trim()) {
      return
    }

    try {
      setError(null)
      
      // Create optimistic message
      const optimisticMsg = addOptimisticMessage(content)
      
      // Send through WebSocket for real-time experience
      wsManager.sendMessage(currentConversation.id, content)
      
      // Send through API for persistence
      await dispatch(sendMessage({ 
        conversationId: currentConversation.id, 
        content, 
        contentType 
      })).unwrap()
      
      // Remove optimistic message on success
      dispatch(removeOptimisticMessage(optimisticMsg.id))
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message')
      // Remove optimistic message on failure
      dispatch(removeOptimisticMessage(optimisticMsg.id))
      throw err
    }
  }, [currentConversation?.id, dispatch])

  const handleEditMessage = useCallback(async (
    messageId: string, 
    newContent: string
  ): Promise<void> => {
    try {
      setError(null)
      await dispatch(updateMessage({ messageId, content: newContent })).unwrap()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to edit message')
      throw err
    }
  }, [dispatch])

  const handleDeleteMessage = useCallback(async (
    messageId: string
  ): Promise<void> => {
    try {
      setError(null)
      await dispatch(deleteMessage(messageId)).unwrap()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete message')
      throw err
    }
  }, [dispatch])

  const handleLoadMoreMessages = useCallback(async (): Promise<void> => {
    if (!currentConversation?.id || !hasMoreMessages || isLoading) {
      return
    }

    try {
      setError(null)
      const oldestMessage = messages[0]
      await dispatch(fetchMessages({ 
        conversationId: currentConversation.id, 
        before: oldestMessage?.created_at,
        limit: 50 
      })).unwrap()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load more messages')
      throw err
    }
  }, [currentConversation?.id, messages, hasMoreMessages, isLoading, dispatch])

  const handleMarkMessagesAsRead = useCallback(async (
    messageIds: string[]
  ): Promise<void> => {
    if (!currentConversation?.id) {
      return
    }

    try {
      setError(null)
      // Mark the last message as read (backend will handle the rest)
      const lastMessageId = messageIds[messageIds.length - 1]
      if (lastMessageId && lastMessageId !== lastReadMessageRef.current) {
        lastReadMessageRef.current = lastMessageId
        await dispatch(markAsRead({ 
          conversationId: currentConversation.id, 
          messageId: lastMessageId 
        })).unwrap()
      }
    } catch (err) {
      console.error('Failed to mark messages as read:', err)
      // Don't show error to user for read receipts
    }
  }, [currentConversation?.id, dispatch])

  const handleSetCurrentConversation = useCallback((
    conversation: Conversation | undefined
  ): void => {
    dispatch(setCurrentConversation(conversation))
  }, [dispatch])

  const handleStartTyping = useCallback((): void => {
    if (!enableTyping || !currentConversation?.id || isTyping) {
      return
    }

    // Set local typing state
    dispatch(setIsTyping(true))
    
    // Send typing indicator via WebSocket
    wsManager.sendTypingStart(currentConversation.id)
    
    // Clear typing indicator after delay
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current)
    }
    
    typingTimeoutRef.current = setTimeout(() => {
      handleStopTyping()
    }, typingDelay)
  }, [enableTyping, currentConversation?.id, isTyping, typingDelay, dispatch])

  const handleStopTyping = useCallback((): void => {
    if (!currentConversation?.id) {
      return
    }

    // Clear local typing state
    dispatch(setIsTyping(false))
    
    // Send typing stop via WebSocket
    wsManager.sendTypingStop(currentConversation.id)
    
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current)
      typingTimeoutRef.current = null
    }
  }, [currentConversation?.id, dispatch])

  const addOptimisticMessage = useCallback((
    content: string
  ): Message => {
    const optimisticMessage: Message = {
      id: `optimistic-${uuidv4()}`,
      conversation_id: currentConversation?.id || '',
      organization_id: currentConversation?.organization_id || '',
      sender_type: 'user',
      sender_id: '', // Will be populated by backend
      content,
      content_type: 'text',
      content_encrypted: false,
      ai_processed: false,
      is_flagged: false,
      is_internal: false,
      is_automated: false,
      is_system_generated: false,
      is_private: false,
      is_edited: false,
      edit_count: 0,
      has_attachments: false,
      attachments: [],
      failed_delivery: false,
      delivery_attempts: 0,
      entities: [],
      keywords: [],
      topics: [],
      metadata: {},
      created_at: new Date().toISOString(),
    }
    
    dispatch(optimisticMessage(optimisticMessage))
    return optimisticMessage
  }, [currentConversation, dispatch])

  const scrollToBottom = useCallback((): void => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [])

  const scrollToMessage = useCallback((
    messageId: string
  ): void => {
    const element = document.querySelector(`[data-message-id="${messageId}"]`)
    if (element && scrollContainerRef.current) {
      element.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      })
    }
  }, [])

  const clearError = useCallback((): void => {
    setError(null)
  }, [])

  return {
    // State
    messages,
    currentConversation,
    isSending,
    isTyping,
    typingUsers,
    
    // Actions
    sendMessage: handleSendMessage,
    editMessage: handleEditMessage,
    deleteMessage: handleDeleteMessage,
    loadMoreMessages: handleLoadMoreMessages,
    markMessagesAsRead: handleMarkMessagesAsRead,
    setCurrentConversation: handleSetCurrentConversation,
    
    // Typing
    startTyping: handleStartTyping,
    stopTyping: handleStopTyping,
    
    // Optimistic updates
    addOptimisticMessage,
    
    // UI helpers
    scrollToBottom,
    scrollToMessage,
    
    // Error handling
    error,
    clearError,
  }
}

// Utility hooks for specific chat functionality
export function useTypingIndicator(
  conversationId: string,
  enabled: boolean = true
): {
  isTyping: boolean
  startTyping: () => void
  stopTyping: () => void
} {
  const [isTyping, setIsTyping] = useState(false)
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const startTyping = useCallback(() => {
    if (!enabled || isTyping) return
    
    setIsTyping(true)
    wsManager.sendTypingStart(conversationId)
    
    // Auto-stop typing after 3 seconds
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current)
    }
    
    typingTimeoutRef.current = setTimeout(() => {
      stopTyping()
    }, 3000)
  }, [conversationId, enabled, isTyping])

  const stopTyping = useCallback(() => {
    if (!isTyping) return
    
    setIsTyping(false)
    wsManager.sendTypingStop(conversationId)
    
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current)
      typingTimeoutRef.current = null
    }
  }, [conversationId, isTyping])

  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current)
      }
    }
  }, [])

  return {
    isTyping,
    startTyping,
    stopTyping,
  }
}

export function useMessageDelivery(
  messageId: string
): {
  isDelivered: boolean
  isSeen: boolean
  deliveryStatus: 'pending' | 'delivered' | 'seen' | 'failed'
} {
  // This would integrate with the store to track message delivery status
  // For now, return a basic implementation
  return {
    isDelivered: false,
    isSeen: false,
    deliveryStatus: 'pending',
  }
}

export function useChatPresence(
  conversationId: string
): {
  onlineUsers: string[]
  isUserOnline: (userId: string) => boolean
} {
  // This would integrate with WebSocket presence indicators
  // For now, return a basic implementation
  return {
    onlineUsers: [],
    isUserOnline: () => false,
  }
}

export default useChat
