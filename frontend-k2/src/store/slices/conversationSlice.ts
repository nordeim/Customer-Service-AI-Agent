import { createSlice, PayloadAction, createAsyncThunk } from '@reduxjs/toolkit'
import { 
  Conversation, 
  Message, 
  ChatState, 
  SendMessageData, 
  ConversationCreateData,
  ConversationFilters,
  SearchOptions,
  AppError,
  TypingIndicatorData 
} from '@/types'
import apiClient from '@/services/api'
import wsManager from '@/services/websocket'

interface ConversationState extends ChatState {
  conversations: Conversation[];
  currentConversation: Conversation | undefined;
  messages: Message[];
  isLoading: boolean;
  isTyping: boolean;
  typingUsers: TypingIndicatorData[];
  hasMoreMessages: boolean;
  isSending: boolean;
  error: AppError | null;
  filters: ConversationFilters;
  searchQuery: string;
  totalConversations: number;
}

const initialState: ConversationState = {
  conversations: [],
  currentConversation: undefined,
  messages: [],
  isLoading: false,
  isTyping: false,
  typingUsers: [],
  hasMoreMessages: true,
  isSending: false,
  error: null,
  filters: {},
  searchQuery: '',
  totalConversations: 0,
}

// Async thunks
export const fetchConversations = createAsyncThunk(
  'conversation/fetchConversations',
  async (params?: { page?: number; limit?: number; filters?: ConversationFilters }) => {
    const response = await apiClient.getConversations({
      page: params?.page || 1,
      limit: params?.limit || 20,
      ...params?.filters,
    })
    return response
  }
)

export const fetchConversation = createAsyncThunk(
  'conversation/fetchConversation',
  async (id: string, { rejectWithValue }) => {
    try {
      const conversation = await apiClient.getConversation(id)
      return conversation
    } catch (error) {
      return rejectWithValue(error)
    }
  }
)

export const createConversation = createAsyncThunk(
  'conversation/createConversation',
  async (data: ConversationCreateData, { rejectWithValue }) => {
    try {
      const conversation = await apiClient.createConversation(data)
      return conversation
    } catch (error) {
      return rejectWithValue(error)
    }
  }
)

export const updateConversation = createAsyncThunk(
  'conversation/updateConversation',
  async ({ id, data }: { id: string; data: Partial<Conversation> }, { rejectWithValue }) => {
    try {
      const conversation = await apiClient.updateConversation(id, data)
      return conversation
    } catch (error) {
      return rejectWithValue(error)
    }
  }
)

export const deleteConversation = createAsyncThunk(
  'conversation/deleteConversation',
  async (id: string, { rejectWithValue }) => {
    try {
      await apiClient.deleteConversation(id)
      return id
    } catch (error) {
      return rejectWithValue(error)
    }
  }
)

export const fetchMessages = createAsyncThunk(
  'conversation/fetchMessages',
  async ({ conversationId, before, after, limit = 50 }: { 
    conversationId: string; 
    before?: string; 
    after?: string; 
    limit?: number 
  }) => {
    const response = await apiClient.getMessages(conversationId, { before, after, limit })
    return { messages: response.data, conversationId, pagination: response.metadata }
  }
)

export const sendMessage = createAsyncThunk(
  'conversation/sendMessage',
  async ({ conversationId, content, contentType }: SendMessageData, { rejectWithValue }) => {
    try {
      const message = await apiClient.sendMessage(conversationId, content, contentType)
      return message
    } catch (error) {
      return rejectWithValue(error)
    }
  }
)

export const updateMessage = createAsyncThunk(
  'conversation/updateMessage',
  async ({ messageId, content }: { messageId: string; content: string }, { rejectWithValue }) => {
    try {
      const message = await apiClient.updateMessage(messageId, content)
      return message
    } catch (error) {
      return rejectWithValue(error)
    }
  }
)

export const deleteMessage = createAsyncThunk(
  'conversation/deleteMessage',
  async (messageId: string, { rejectWithValue }) => {
    try {
      await apiClient.deleteMessage(messageId)
      return messageId
    } catch (error) {
      return rejectWithValue(error)
    }
  }
)

export const markAsRead = createAsyncThunk(
  'conversation/markAsRead',
  async ({ conversationId, messageId }: { conversationId: string; messageId: string }) => {
    await apiClient.markAsRead(conversationId, messageId)
    return { conversationId, messageId }
  }
)

export const searchConversations = createAsyncThunk(
  'conversation/searchConversations',
  async (options: SearchOptions) => {
    // This would be implemented with a search endpoint
    const response = await apiClient.getConversations({
      search: options.query,
      ...options.filters,
      page: options.page,
      limit: options.limit,
    })
    return response
  }
)

const conversationSlice = createSlice({
  name: 'conversation',
  initialState,
  reducers: {
    setCurrentConversation: (state, action: PayloadAction<Conversation | undefined>) => {
      state.currentConversation = action.payload
      if (action.payload) {
        // Join WebSocket room for this conversation
        wsManager.joinConversation(action.payload.id)
      }
    },
    addMessage: (state, action: PayloadAction<Message>) => {
      const message = action.payload
      const existingIndex = state.messages.findIndex(m => m.id === message.id)
      
      if (existingIndex >= 0) {
        // Update existing message
        state.messages[existingIndex] = message
      } else {
        // Add new message and maintain chronological order
        state.messages.push(message)
        state.messages.sort((a, b) => 
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        )
      }
      
      // Update current conversation if this is the active one
      if (state.currentConversation?.id === message.conversation_id) {
        state.currentConversation.last_message_at = message.created_at
        state.currentConversation.last_activity_at = message.created_at
        
        // Update message counts
        if (message.sender_type === 'user') {
          state.currentConversation.user_message_count++
        } else if (message.sender_type === 'ai_agent' || message.sender_type === 'human_agent') {
          state.currentConversation.agent_message_count++
        }
        
        if (message.sender_type === 'ai_agent') {
          state.currentConversation.ai_message_count++
        }
        
        state.currentConversation.message_count++
      }
    },
    updateMessage: (state, action: PayloadAction<Message>) => {
      const message = action.payload
      const index = state.messages.findIndex(m => m.id === message.id)
      if (index >= 0) {
        state.messages[index] = message
      }
    },
    deleteMessage: (state, action: PayloadAction<string>) => {
      const messageId = action.payload
      state.messages = state.messages.filter(m => m.id !== messageId)
    },
    setTypingIndicator: (state, action: PayloadAction<TypingIndicatorData>) => {
      const data = action.payload
      const existingIndex = state.typingUsers.findIndex(
        u => u.conversation_id === data.conversation_id && u.user_id === data.user_id
      )
      
      if (data.is_typing) {
        if (existingIndex >= 0) {
          state.typingUsers[existingIndex] = data
        } else {
          state.typingUsers.push(data)
        }
      } else {
        state.typingUsers = state.typingUsers.filter(
          u => !(u.conversation_id === data.conversation_id && u.user_id === data.user_id)
        )
      }
    },
    setIsTyping: (state, action: PayloadAction<boolean>) => {
      state.isTyping = action.payload
    },
    setFilters: (state, action: PayloadAction<ConversationFilters>) => {
      state.filters = action.payload
    },
    setSearchQuery: (state, action: PayloadAction<string>) => {
      state.searchQuery = action.payload
    },
    clearMessages: (state) => {
      state.messages = []
      state.hasMoreMessages = true
    },
    clearError: (state) => {
      state.error = null
    },
    optimisticMessage: (state, action: PayloadAction<Message>) => {
      // Add message optimistically before server confirmation
      state.messages.push(action.payload)
      state.isSending = true
    },
    removeOptimisticMessage: (state, action: PayloadAction<string>) => {
      // Remove optimistic message when server responds
      state.messages = state.messages.filter(m => m.id !== action.payload)
      state.isSending = false
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch conversations
      .addCase(fetchConversations.pending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addCase(fetchConversations.fulfilled, (state, action) => {
        state.conversations = action.payload.data
        state.totalConversations = action.payload.metadata.total
        state.isLoading = false
      })
      .addCase(fetchConversations.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload as AppError
      })
      // Fetch conversation
      .addCase(fetchConversation.pending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addCase(fetchConversation.fulfilled, (state, action) => {
        const conversation = action.payload
        // Update in conversations list
        const index = state.conversations.findIndex(c => c.id === conversation.id)
        if (index >= 0) {
          state.conversations[index] = conversation
        } else {
          state.conversations.unshift(conversation)
        }
        state.currentConversation = conversation
        state.isLoading = false
      })
      .addCase(fetchConversation.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload as AppError
      })
      // Create conversation
      .addCase(createConversation.pending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addCase(createConversation.fulfilled, (state, action) => {
        state.conversations.unshift(action.payload)
        state.currentConversation = action.payload
        state.isLoading = false
        // Clear messages for new conversation
        state.messages = []
        state.hasMoreMessages = true
      })
      .addCase(createConversation.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload as AppError
      })
      // Update conversation
      .addCase(updateConversation.fulfilled, (state, action) => {
        const updatedConversation = action.payload
        const index = state.conversations.findIndex(c => c.id === updatedConversation.id)
        if (index >= 0) {
          state.conversations[index] = updatedConversation
        }
        if (state.currentConversation?.id === updatedConversation.id) {
          state.currentConversation = updatedConversation
        }
      })
      // Delete conversation
      .addCase(deleteConversation.fulfilled, (state, action) => {
        const conversationId = action.payload
        state.conversations = state.conversations.filter(c => c.id !== conversationId)
        if (state.currentConversation?.id === conversationId) {
          state.currentConversation = undefined
          state.messages = []
          state.hasMoreMessages = true
        }
      })
      // Fetch messages
      .addCase(fetchMessages.pending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addCase(fetchMessages.fulfilled, (state, action) => {
        const { messages, pagination } = action.payload
        
        if (pagination.page === 1) {
          // First page or refresh - replace messages
          state.messages = messages
        } else {
          // Load more - append messages
          const existingIds = new Set(state.messages.map(m => m.id))
          const newMessages = messages.filter(m => !existingIds.has(m.id))
          state.messages = [...state.messages, ...newMessages]
          // Sort by created_at to maintain chronological order
          state.messages.sort((a, b) => 
            new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          )
        }
        
        state.hasMoreMessages = pagination.has_next || false
        state.isLoading = false
      })
      .addCase(fetchMessages.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload as AppError
      })
      // Send message
      .addCase(sendMessage.pending, (state) => {
        state.isSending = true
        state.error = null
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        // Replace optimistic message with real one
        const sentMessage = action.payload
        const index = state.messages.findIndex(m => m.id === sentMessage.id)
        if (index >= 0) {
          state.messages[index] = sentMessage
        } else {
          state.messages.push(sentMessage)
          state.messages.sort((a, b) => 
            new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          )
        }
        state.isSending = false
        
        // Update current conversation
        if (state.currentConversation?.id === sentMessage.conversation_id) {
          state.currentConversation.last_message_at = sentMessage.created_at
          state.currentConversation.last_activity_at = sentMessage.created_at
        }
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.isSending = false
        state.error = action.payload as AppError
        // Remove optimistic message on failure
        if (action.meta.arg) {
          state.messages = state.messages.filter(m => m.id !== action.meta.arg.id)
        }
      })
      // Update message
      .addCase(updateMessage.fulfilled, (state, action) => {
        const updatedMessage = action.payload
        const index = state.messages.findIndex(m => m.id === updatedMessage.id)
        if (index >= 0) {
          state.messages[index] = updatedMessage
        }
      })
      // Delete message
      .addCase(deleteMessage.fulfilled, (state, action) => {
        const messageId = action.payload
        state.messages = state.messages.filter(m => m.id !== messageId)
      })
      // Mark as read
      .addCase(markAsRead.fulfilled, (state, action) => {
        const { messageId } = action.payload
        const message = state.messages.find(m => m.id === messageId)
        if (message) {
          message.seen_at = new Date().toISOString()
        }
      })
      // Search conversations
      .addCase(searchConversations.pending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addCase(searchConversations.fulfilled, (state, action) => {
        state.conversations = action.payload.data
        state.totalConversations = action.payload.metadata.total
        state.isLoading = false
      })
      .addCase(searchConversations.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload as AppError
      })
  },
})

export const {
  setCurrentConversation,
  addMessage,
  updateMessage,
  deleteMessage,
  setTypingIndicator,
  setIsTyping,
  setFilters,
  setSearchQuery,
  clearMessages,
  clearError,
  optimisticMessage,
  removeOptimisticMessage,
} = conversationSlice.actions

// Selectors
export const selectConversations = (state: { conversation: ConversationState }) => state.conversation.conversations
export const selectCurrentConversation = (state: { conversation: ConversationState }) => state.conversation.currentConversation
export const selectMessages = (state: { conversation: ConversationState }) => state.conversation.messages
export const selectIsLoading = (state: { conversation: ConversationState }) => state.conversation.isLoading
export const selectIsSending = (state: { conversation: ConversationState }) => state.conversation.isSending
export const selectIsTyping = (state: { conversation: ConversationState }) => state.conversation.isTyping
export const selectTypingUsers = (state: { conversation: ConversationState }) => state.conversation.typingUsers
export const selectHasMoreMessages = (state: { conversation: ConversationState }) => state.conversation.hasMoreMessages
export const selectConversationError = (state: { conversation: ConversationState }) => state.conversation.error
export const selectFilters = (state: { conversation: ConversationState }) => state.conversation.filters
export const selectSearchQuery = (state: { conversation: ConversationState }) => state.conversation.searchQuery
export const selectTotalConversations = (state: { conversation: ConversationState }) => state.conversation.totalConversations

// Memoized selectors
export const selectUnreadCount = (state: { conversation: ConversationState }) => {
  return state.conversation.conversations.filter(c => 
    c.status === 'active' && c.last_message_at && c.last_message_at > (state.conversation.currentConversation?.last_read_at || '')
  ).length
}

export const selectActiveConversations = (state: { conversation: ConversationState }) => {
  return state.conversation.conversations.filter(c => 
    c.status === 'active' || c.status === 'waiting_for_user' || c.status === 'processing'
  )
}

export const selectConversationsByStatus = (status: ConversationStatus) => 
  (state: { conversation: ConversationState }) => {
    return state.conversation.conversations.filter(c => c.status === status)
  }

export const selectMessagesByConversation = (conversationId: string) => 
  (state: { conversation: ConversationState }) => {
    return state.conversation.messages.filter(m => m.conversation_id === conversationId)
  }

export const selectLastMessage = (state: { conversation: ConversationState }) => {
  return state.conversation.messages[state.conversation.messages.length - 1]
}

export default conversationSlice.reducer
