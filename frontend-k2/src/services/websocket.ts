import { io, Socket } from 'socket.io-client'
import { WebSocketMessage, TypingIndicatorData, Message, Conversation } from '@/types'
import { store } from '@/store'
import { addMessage, updateConversation, setTypingIndicator } from '@/store/slices/conversationSlice'
import toast from 'react-hot-toast'

class WebSocketManager {
  private socket: Socket | null = null
  private url: string
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectInterval = 1000
  private isIntentionallyDisconnected = false
  private messageQueue: any[] = []
  private isConnected = false

  constructor(url: string = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws') {
    this.url = url
  }

  connect(authToken?: string): void {
    if (this.socket?.connected) {
      console.log('WebSocket already connected')
      return
    }

    this.isIntentionallyDisconnected = false
    this.reconnectAttempts = 0

    this.socket = io(this.url, {
      transports: ['websocket'],
      auth: authToken ? { token: authToken } : undefined,
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: this.reconnectInterval,
      reconnectionDelayMax: 5000,
      timeout: 20000,
      forceNew: true,
    })

    this.setupEventListeners()
  }

  private setupEventListeners(): void {
    if (!this.socket) return

    this.socket.on('connect', () => {
      console.log('WebSocket connected')
      this.isConnected = true
      this.reconnectAttempts = 0
      this.flushMessageQueue()
      toast.success('Connected to server', { id: 'ws-connect' })
    })

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason)
      this.isConnected = false
      
      if (reason === 'io server disconnect') {
        // Server initiated disconnect, don't reconnect automatically
        this.isIntentionallyDisconnected = true
      } else if (!this.isIntentionallyDisconnected) {
        // Client initiated or network disconnect, attempt reconnection
        this.handleReconnection()
      }
    })

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error)
      this.isConnected = false
      this.handleConnectionError(error)
    })

    this.socket.on('error', (error) => {
      console.error('WebSocket error:', error)
      toast.error('Connection error occurred')
    })

    // Message events
    this.socket.on('message', (data: WebSocketMessage) => {
      this.handleMessage(data)
    })

    this.socket.on('new_message', (message: Message) => {
      this.handleNewMessage(message)
    })

    this.socket.on('message_updated', (message: Message) => {
      this.handleMessageUpdated(message)
    })

    this.socket.on('message_deleted', (data: { message_id: string; conversation_id: string }) => {
      this.handleMessageDeleted(data)
    })

    // Typing indicator events
    this.socket.on('typing_start', (data: TypingIndicatorData) => {
      this.handleTypingStart(data)
    })

    this.socket.on('typing_stop', (data: TypingIndicatorData) => {
      this.handleTypingStop(data)
    })

    // Conversation events
    this.socket.on('conversation_updated', (conversation: Conversation) => {
      this.handleConversationUpdated(conversation)
    })

    this.socket.on('conversation_created', (conversation: Conversation) => {
      this.handleConversationCreated(conversation)
    })

    this.socket.on('conversation_deleted', (data: { conversation_id: string }) => {
      this.handleConversationDeleted(data)
    })

    // Status events
    this.socket.on('status_change', (data: { conversation_id: string; status: string }) => {
      this.handleStatusChange(data)
    })

    // Error events
    this.socket.on('error_event', (data: { code: string; message: string; details?: any }) => {
      this.handleError(data)
    })

    // Presence events
    this.socket.on('user_online', (data: { user_id: string; conversation_id?: string }) => {
      this.handleUserOnline(data)
    })

    this.socket.on('user_offline', (data: { user_id: string; conversation_id?: string }) => {
      this.handleUserOffline(data)
    })
  }

  private handleReconnection(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      toast.error('Unable to connect to server. Please check your connection.', {
        id: 'ws-reconnect-failed',
        duration: 5000,
      })
      return
    }

    this.reconnectAttempts++
    const delay = Math.min(this.reconnectInterval * Math.pow(2, this.reconnectAttempts), 5000)
    
    console.log(`Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`)
    
    setTimeout(() => {
      if (!this.isIntentionallyDisconnected && !this.isConnected) {
        this.connect()
      }
    }, delay)
  }

  private handleConnectionError(error: Error): void {
    if (error.message.includes('401')) {
      toast.error('Authentication failed. Please log in again.', { id: 'ws-auth-error' })
      // Redirect to login
      window.location.href = '/login'
    } else if (error.message.includes('403')) {
      toast.error('Access denied. Please check your permissions.', { id: 'ws-forbidden' })
    } else {
      toast.error('Connection failed. Attempting to reconnect...', { id: 'ws-connect-error' })
    }
  }

  private handleMessage(data: WebSocketMessage): void {
    console.log('WebSocket message received:', data)
    
    switch (data.type) {
      case 'error':
        toast.error(data.data?.message || 'An error occurred')
        break
      case 'connection':
        console.log('Connection status:', data.data)
        break
      default:
        console.log('Unknown message type:', data.type)
    }
  }

  private handleNewMessage(message: Message): void {
    console.log('New message received:', message)
    
    // Add message to store
    store.dispatch(addMessage(message))
    
    // Handle notifications
    if (message.sender_type !== 'user' && !document.hidden) {
      // Show notification for non-user messages when tab is visible
      this.showNotification('New message', {
        body: message.content_preview || message.content,
        tag: message.id,
      })
    }
  }

  private handleMessageUpdated(message: Message): void {
    console.log('Message updated:', message)
    // Update message in store
    store.dispatch(addMessage(message)) // This will update existing message
  }

  private handleMessageDeleted(data: { message_id: string; conversation_id: string }): void {
    console.log('Message deleted:', data)
    // Remove message from store
    // This would require a deleteMessage action in the store
  }

  private handleTypingStart(data: TypingIndicatorData): void {
    console.log('Typing started:', data)
    store.dispatch(setTypingIndicator({ ...data, is_typing: true }))
  }

  private handleTypingStop(data: TypingIndicatorData): void {
    console.log('Typing stopped:', data)
    store.dispatch(setTypingIndicator({ ...data, is_typing: false }))
  }

  private handleConversationUpdated(conversation: Conversation): void {
    console.log('Conversation updated:', conversation)
    store.dispatch(updateConversation(conversation))
  }

  private handleConversationCreated(conversation: Conversation): void {
    console.log('Conversation created:', conversation)
    // Handle new conversation creation
    // This might trigger UI updates or navigation
  }

  private handleConversationDeleted(data: { conversation_id: string }): void {
    console.log('Conversation deleted:', data)
    // Handle conversation deletion
    // This might trigger navigation or UI updates
  }

  private handleStatusChange(data: { conversation_id: string; status: string }): void {
    console.log('Status changed:', data)
    // Update conversation status in store
    // This would require a status update action
  }

  private handleError(data: { code: string; message: string; details?: any }): void {
    console.error('WebSocket error:', data)
    toast.error(data.message || 'An error occurred')
  }

  private handleUserOnline(data: { user_id: string; conversation_id?: string }): void {
    console.log('User online:', data)
    // Update user presence in store
  }

  private handleUserOffline(data: { user_id: string; conversation_id?: string }): void {
    console.log('User offline:', data)
    // Update user presence in store
  }

  private showNotification(title: string, options: NotificationOptions): void {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(title, options)
    }
  }

  // Public methods for sending events
  sendMessage(conversationId: string, content: string): void {
    if (!this.isConnected) {
      console.warn('WebSocket not connected, queuing message')
      this.messageQueue.push({ type: 'message', conversationId, content })
      return
    }

    this.socket?.emit('send_message', {
      conversation_id: conversationId,
      content,
      timestamp: new Date().toISOString(),
    })
  }

  sendTypingStart(conversationId: string): void {
    if (!this.isConnected) return

    this.socket?.emit('typing_start', {
      conversation_id: conversationId,
      timestamp: new Date().toISOString(),
    })
  }

  sendTypingStop(conversationId: string): void {
    if (!this.isConnected) return

    this.socket?.emit('typing_stop', {
      conversation_id: conversationId,
      timestamp: new Date().toISOString(),
    })
  }

  joinConversation(conversationId: string): void {
    if (!this.isConnected) return

    this.socket?.emit('join_conversation', {
      conversation_id: conversationId,
    })
  }

  leaveConversation(conversationId: string): void {
    if (!this.isConnected) return

    this.socket?.emit('leave_conversation', {
      conversation_id: conversationId,
    })
  }

  markAsRead(conversationId: string, messageId: string): void {
    if (!this.isConnected) return

    this.socket?.emit('mark_as_read', {
      conversation_id: conversationId,
      message_id: messageId,
    })
  }

  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift()
      if (message) {
        this.socket?.emit(message.type, message)
      }
    }
  }

  requestNotificationPermission(): void {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission()
    }
  }

  disconnect(): void {
    this.isIntentionallyDisconnected = true
    this.socket?.disconnect()
    this.socket = null
    this.isConnected = false
  }

  getConnectionStatus(): boolean {
    return this.isConnected
  }

  getReconnectAttempts(): number {
    return this.reconnectAttempts
  }
}

// Create singleton instance
const wsManager = new WebSocketManager()

export default wsManager
