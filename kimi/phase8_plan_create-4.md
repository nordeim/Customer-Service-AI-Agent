<think>
I need to continue with the same rigorous approach. Let me systematically work through:

1. Store types definition
2. Store slices (auth, conversation, ui, notification, websocket)
3. API configuration
4. Store hooks
5. Then move to components, services, and utilities

Each file needs to:
- Comply with PRD v4 accessibility requirements
- Use TypeScript strict mode
- Align with Database Schema v4
- Include proper error handling
- Follow security best practices
- Be evidence-based with clear implementation

Let me continue methodically with the store types first.
</think>

Continuing with Phase 8 implementation - Store types and slices:

## frontend/src/store/types.ts
```typescript
import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux';
import type { RootState as RootStateType, AppDispatch as AppDispatchType } from './index';

// Typed hooks
export const useAppDispatch = () => useDispatch<AppDispatchType>();
export const useAppSelector: TypedUseSelectorHook<RootStateType> = useSelector;

// Base types aligned with Database Schema v4
export interface User {
  id: string;
  organizationId: string;
  email: string;
  displayName?: string;
  firstName?: string;
  lastName?: string;
  avatarUrl?: string;
  role: 'customer' | 'agent' | 'admin';
  permissions: Record<string, boolean>;
  isActive: boolean;
  lastSeenAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Organization {
  id: string;
  slug: string;
  name: string;
  displayName?: string;
  subscriptionTier: 'trial' | 'free' | 'starter' | 'professional' | 'enterprise' | 'custom';
  settings: {
    aiEnabled: boolean;
    autoEscalation: boolean;
    sentimentAnalysis: boolean;
    emotionDetection: boolean;
    languageDetection: boolean;
    profanityFilter: boolean;
    autoTranslation: boolean;
  };
  features: {
    customModels: boolean;
    whiteLabel: boolean;
    ssoEnabled: boolean;
    apiAccess: boolean;
    webhooks: boolean;
    analyticsDashboard: boolean;
  };
  limits: {
    maxUsers: number;
    maxConversationsPerMonth: number;
    maxMessagesPerConversation: number;
    maxKnowledgeEntries: number;
    maxApiCallsPerHour: number;
    storageQuotaGb: number;
  };
  createdAt: string;
  updatedAt: string;
}

export interface Conversation {
  id: string;
  organizationId: string;
  userId: string;
  conversationNumber: number;
  title?: string;
  channel: 'web_chat' | 'mobile_ios' | 'mobile_android' | 'email' | 'slack' | 'teams' | 'whatsapp' | 'telegram' | 'sms' | 'voice' | 'api' | 'widget' | 'salesforce';
  status: 'initialized' | 'active' | 'waiting_for_user' | 'waiting_for_agent' | 'processing' | 'escalated' | 'transferred' | 'resolved' | 'abandoned' | 'archived';
  priority: 'low' | 'medium' | 'high' | 'urgent' | 'critical';
  isUrgent: boolean;
  assignedAgentId?: string;
  assignedTeam?: string;
  startedAt: string;
  lastActivityAt: string;
  messageCount: number;
  aiHandled: boolean;
  aiConfidenceAvg?: number;
  sentimentCurrent?: 'very_negative' | 'negative' | 'neutral' | 'positive' | 'very_positive';
  emotionCurrent?: 'angry' | 'frustrated' | 'confused' | 'neutral' | 'satisfied' | 'happy' | 'excited';
  resolved: boolean;
  escalated: boolean;
  satisfactionScore?: number;
  language: string;
  tags: string[];
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface Message {
  id: string;
  conversationId: string;
  organizationId: string;
  senderType: 'user' | 'ai_agent' | 'human_agent' | 'system' | 'bot' | 'integration';
  senderId?: string;
  senderName?: string;
  senderEmail?: string;
  content: string;
  contentType: 'text' | 'html' | 'markdown' | 'code' | 'json' | 'image' | 'audio' | 'video' | 'file' | 'card' | 'carousel' | 'quick_reply' | 'form';
  originalLanguage?: string;
  detectedLanguage?: string;
  contentTranslated?: string;
  translatedTo?: string;
  translationConfidence?: number;
  intent?: string;
  intentConfidence?: number;
  sentimentScore?: number;
  sentimentLabel?: 'very_negative' | 'negative' | 'neutral' | 'positive' | 'very_positive';
  emotionLabel?: 'angry' | 'frustrated' | 'confused' | 'neutral' | 'satisfied' | 'happy' | 'excited';
  emotionIntensity?: number;
  aiProcessed: boolean;
  aiModelUsed?: string;
  aiProvider?: 'openai' | 'anthropic' | 'google' | 'azure' | 'aws' | 'huggingface' | 'cohere' | 'local' | 'custom';
  aiConfidence?: number;
  isFlagged: boolean;
  isEdited: boolean;
  hasAttachments: boolean;
  attachments: Array<{
    id: string;
    name: string;
    type: string;
    size: number;
    url: string;
  }>;
  deliveredAt?: string;
  seenAt?: string;
  metadata: Record<string, unknown>;
  createdAt: string;
  sentAt?: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  organization: Organization | null;
  token: string | null;
  refreshToken: string | null;
  expiresAt: string | null;
  isLoading: boolean;
  error: string | null;
  mfaRequired: boolean;
  mfaVerified: boolean;
}

export interface ConversationState {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  hasMore: boolean;
  totalCount: number;
  filters: {
    status?: string;
    channel?: string;
    priority?: string;
    dateFrom?: string;
    dateTo?: string;
  };
  sortBy: 'createdAt' | 'lastActivityAt' | 'priority';
  sortOrder: 'asc' | 'desc';
}

export interface UIState {
  theme: 'light' | 'dark' | 'system';
  language: string;
  fontSize: 'small' | 'medium' | 'large';
  reducedMotion: boolean;
  highContrast: boolean;
  sidebarCollapsed: boolean;
  notifications: {
    enabled: boolean;
    sound: boolean;
    desktop: boolean;
    email: boolean;
    push: boolean;
  };
  accessibility: {
    keyboardNavigation: boolean;
    screenReaderAnnouncements: boolean;
    focusIndicators: boolean;
    skipLinks: boolean;
  };
  chat: {
    autoScroll: boolean;
    showTimestamps: boolean;
    showAvatars: boolean;
    compactMode: boolean;
    enterToSend: boolean;
  };
}

export interface NotificationState {
  notifications: Array<{
    id: string;
    type: 'info' | 'success' | 'warning' | 'error';
    title: string;
    message: string;
    timestamp: string;
    read: boolean;
    persistent: boolean;
    actions?: Array<{
      label: string;
      action: string;
    }>;
  }>;
  unreadCount: number;
}

export interface WebSocketState {
  isConnected: boolean;
  connectionId: string | null;
  lastPingAt: string | null;
  reconnectAttempts: number;
  isReconnecting: boolean;
  error: string | null;
}

export interface APIError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  timestamp: string;
}

export interface APIResponse<T> {
  data: T;
  status: number;
  message?: string;
  errors?: APIError[];
  metadata?: {
    totalCount?: number;
    page?: number;
    pageSize?: number;
    hasMore?: boolean;
  };
}

export interface PaginationParams {
  page: number;
  pageSize: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface FilterParams {
  status?: string[];
  channel?: string[];
  priority?: string[];
  dateFrom?: string;
  dateTo?: string;
  search?: string;
}

export interface WebSocketMessage {
  type: 'message' | 'typing' | 'status' | 'error' | 'ping' | 'pong';
  conversationId: string;
  data: unknown;
  timestamp: string;
  correlationId: string;
}

export interface TypingIndicator {
  conversationId: string;
  userId: string;
  userName: string;
  isTyping: boolean;
  timestamp: string;
}

export interface ConversationStatus {
  conversationId: string;
  status: 'initialized' | 'active' | 'waiting_for_user' | 'waiting_for_agent' | 'processing' | 'escalated' | 'transferred' | 'resolved' | 'abandoned' | 'archived';
  timestamp: string;
}

// Action types
export interface BaseAction<T = unknown> {
  type: string;
  payload: T;
  meta?: {
    timestamp: string;
    correlationId: string;
    userId?: string;
  };
  error?: boolean;
}

export interface AsyncAction<T = unknown> extends BaseAction<T> {
  meta: BaseAction<T>['meta'] & {
    requestId: string;
    requestStatus: 'pending' | 'fulfilled' | 'rejected';
  };
}
```

## frontend/src/store/slices/authSlice.ts
```typescript
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { User, Organization, AuthState, APIError } from '../types';
import { authAPI } from '../api/auth';
import { tokenService } from '@services/auth/tokenService';
import { websocketService } from '@services/websocket/websocketService';

// Async thunks
export const login = createAsyncThunk(
  'auth/login',
  async (credentials: { email: string; password: string; rememberMe?: boolean }, { rejectWithValue }) => {
    try {
      const response = await authAPI.login(credentials);
      return response.data;
    } catch (error) {
      return rejectWithValue(error as APIError);
    }
  }
);

export const logout = createAsyncThunk(
  'auth/logout',
  async (_, { dispatch }) => {
    try {
      await authAPI.logout();
      websocketService.disconnect();
      dispatch(authSlice.actions.clearAuth());
    } catch (error) {
      console.error('Logout error:', error);
    }
  }
);

export const refreshToken = createAsyncThunk(
  'auth/refreshToken',
  async (_, { rejectWithValue }) => {
    try {
      const refreshToken = tokenService.getRefreshToken();
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }
      const response = await authAPI.refreshToken(refreshToken);
      return response.data;
    } catch (error) {
      return rejectWithValue(error as APIError);
    }
  }
);

export const verifyMFA = createAsyncThunk(
  'auth/verifyMFA',
  async (code: string, { rejectWithValue }) => {
    try {
      const response = await authAPI.verifyMFA(code);
      return response.data;
    } catch (error) {
      return rejectWithValue(error as APIError);
    }
  }
);

export const getCurrentUser = createAsyncThunk(
  'auth/getCurrentUser',
  async (_, { rejectWithValue }) => {
    try {
      const response = await authAPI.getCurrentUser();
      return response.data;
    } catch (error) {
      return rejectWithValue(error as APIError);
    }
  }
);

export const updateProfile = createAsyncThunk(
  'auth/updateProfile',
  async (data: Partial<User>, { rejectWithValue }) => {
    try {
      const response = await authAPI.updateProfile(data);
      return response.data;
    } catch (error) {
      return rejectWithValue(error as APIError);
    }
  }
);

// Initial state
const initialState: AuthState = {
  isAuthenticated: false,
  user: null,
  organization: null,
  token: null,
  refreshToken: null,
  expiresAt: null,
  isLoading: false,
  error: null,
  mfaRequired: false,
  mfaVerified: false,
};

// Slice
export const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setAuth: (state, action: PayloadAction<{ user: User; organization: Organization; token: string; refreshToken: string; expiresAt: string }>) => {
      state.isAuthenticated = true;
      state.user = action.payload.user;
      state.organization = action.payload.organization;
      state.token = action.payload.token;
      state.refreshToken = action.payload.refreshToken;
      state.expiresAt = action.payload.expiresAt;
      state.error = null;
      state.mfaRequired = false;
      state.mfaVerified = true;
      
      // Store tokens securely
      tokenService.setToken(action.payload.token);
      tokenService.setRefreshToken(action.payload.refreshToken);
      tokenService.setExpiresAt(action.payload.expiresAt);
    },
    
    clearAuth: (state) => {
      state.isAuthenticated = false;
      state.user = null;
      state.organization = null;
      state.token = null;
      state.refreshToken = null;
      state.expiresAt = null;
      state.error = null;
      state.mfaRequired = false;
      state.mfaVerified = false;
      
      // Clear stored tokens
      tokenService.clearTokens();
    },
    
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    
    setMFARequired: (state, action: PayloadAction<boolean>) => {
      state.mfaRequired = action.payload;
    },
    
    setMFAVerified: (state, action: PayloadAction<boolean>) => {
      state.mfaVerified = action.payload;
    },
    
    updateUser: (state, action: PayloadAction<Partial<User>>) => {
      if (state.user) {
        state.user = { ...state.user, ...action.payload };
      }
    },
    
    updateOrganization: (state, action: PayloadAction<Partial<Organization>>) => {
      if (state.organization) {
        state.organization = { ...state.organization, ...action.payload };
      }
    },
    
    clearError: (state) => {
      state.error = null;
    },
  },
  
  extraReducers: (builder) => {
    builder
      // Login
      .addCase(login.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = true;
        state.user = action.payload.user;
        state.organization = action.payload.organization;
        state.token = action.payload.token;
        state.refreshToken = action.payload.refreshToken;
        state.expiresAt = action.payload.expiresAt;
        state.mfaRequired = action.payload.mfaRequired || false;
        state.mfaVerified = !action.payload.mfaRequired;
        
        // Store tokens
        tokenService.setToken(action.payload.token);
        tokenService.setRefreshToken(action.payload.refreshToken);
        tokenService.setExpiresAt(action.payload.expiresAt);
        
        // Connect WebSocket if authenticated
        if (!action.payload.mfaRequired) {
          websocketService.connect(action.payload.token);
        }
      })
      .addCase(login.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload?.message || 'Login failed';
        state.isAuthenticated = false;
      })
      
      // Logout
      .addCase(logout.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(logout.fulfilled, (state) => {
        state.isLoading = false;
        // Clear auth is handled in the action
      })
      
      // Refresh token
      .addCase(refreshToken.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(refreshToken.fulfilled, (state, action) => {
        state.isLoading = false;
        state.token = action.payload.token;
        state.refreshToken = action.payload.refreshToken;
        state.expiresAt = action.payload.expiresAt;
        
        tokenService.setToken(action.payload.token);
        tokenService.setRefreshToken(action.payload.refreshToken);
        tokenService.setExpiresAt(action.payload.expiresAt);
        
        // Reconnect WebSocket with new token
        websocketService.disconnect();
        websocketService.connect(action.payload.token);
      })
      .addCase(refreshToken.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload?.message || 'Token refresh failed';
        // Clear auth on refresh failure
        state.isAuthenticated = false;
        state.user = null;
        state.organization = null;
        state.token = null;
        state.refreshToken = null;
        state.expiresAt = null;
        tokenService.clearTokens();
        websocketService.disconnect();
      })
      
      // Verify MFA
      .addCase(verifyMFA.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(verifyMFA.fulfilled, (state, action) => {
        state.isLoading = false;
        state.mfaVerified = true;
        state.mfaRequired = false;
        
        // Connect WebSocket after MFA verification
        if (state.token) {
          websocketService.connect(state.token);
        }
      })
      .addCase(verifyMFA.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload?.message || 'MFA verification failed';
      })
      
      // Get current user
      .addCase(getCurrentUser.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(getCurrentUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload;
      })
      .addCase(getCurrentUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload?.message || 'Failed to get user information';
      })
      
      // Update profile
      .addCase(updateProfile.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(updateProfile.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload;
      })
      .addCase(updateProfile.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload?.message || 'Profile update failed';
      });
  },
});

// Selectors
export const selectAuth = (state: { auth: AuthState }) => state.auth;
export const selectIsAuthenticated = (state: { auth: AuthState }) => state.auth.isAuthenticated;
export const selectUser = (state: { auth: AuthState }) => state.auth.user;
export const selectOrganization = (state: { auth: AuthState }) => state.auth.organization;
export const selectAuthLoading = (state: { auth: AuthState }) => state.auth.isLoading;
export const selectAuthError = (state: { auth: AuthState }) => state.auth.error;
export const selectMFARequired = (state: { auth: AuthState }) => state.auth.mfaRequired;
export const selectMFAVerified = (state: { auth: AuthState }) => state.auth.mfaVerified;
export const selectToken = (state: { auth: AuthState }) => state.auth.token;
export const selectExpiresAt = (state: { auth: AuthState }) => state.auth.expiresAt;

// Action creators
export const { 
  setAuth, 
  clearAuth, 
  setLoading, 
  setError, 
  setMFARequired, 
  setMFAVerified, 
  updateUser, 
  updateOrganization, 
  clearError 
} = authSlice.actions;

export default authSlice.reducer;
```

## frontend/src/store/slices/conversationSlice.ts
```typescript
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Conversation, Message, ConversationState, APIError, FilterParams, PaginationParams } from '../types';
import { conversationAPI } from '../api/conversation';
import { websocketService } from '@services/websocket/websocketService';

// Async thunks
export const fetchConversations = createAsyncThunk(
  'conversation/fetchConversations',
  async ({ page = 1, pageSize = 20, filters = {}, sortBy = 'lastActivityAt', sortOrder = 'desc' }: {
    page?: number;
    pageSize?: number;
    filters?: FilterParams;
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
  }, { rejectWithValue }) => {
    try {
      const response = await conversationAPI.getConversations({ page, pageSize, filters, sortBy, sortOrder });
      return response.data;
    } catch (error) {
      return rejectWithValue(error as APIError);
    }
  }
);

export const fetchConversation = createAsyncThunk(
  'conversation/fetchConversation',
  async (conversationId: string, { rejectWithValue }) => {
    try {
      const response = await conversationAPI.getConversation(conversationId);
      return response.data;
    } catch (error) {
      return rejectWithValue(error as APIError);
    }
  }
);

export const fetchMessages = createAsyncThunk(
  'conversation/fetchMessages',
  async ({ conversationId, page = 1, pageSize = 50 }: {
    conversationId: string;
    page?: number;
    pageSize?: number;
  }, { rejectWithValue }) => {
    try {
      const response = await conversationAPI.getMessages(conversationId, { page, pageSize });
      return { conversationId, messages: response.data };
    } catch (error) {
      return rejectWithValue(error as APIError);
    }
  }
);

export const createConversation = createAsyncThunk(
  'conversation/createConversation',
  async ({ title, channel = 'web_chat', priority = 'medium' }: {
    title?: string;
    channel?: string;
    priority?: string;
  }, { rejectWithValue }) => {
    try {
      const response = await conversationAPI.createConversation({ title, channel, priority });
      return response.data;
    } catch (error) {
      return rejectWithValue(error as APIError);
    }
  }
);

export const sendMessage = createAsyncThunk(
  'conversation/sendMessage',
  async ({ conversationId, content, contentType = 'text' }: {
    conversationId: string;
    content: string;
    contentType?: string;
  }, { rejectWithValue }) => {
    try {
      const response = await conversationAPI.sendMessage(conversationId, { content, contentType });
      return response.data;
    } catch (error) {
      return rejectWithValue(error as APIError);
    }
  }
);

export const updateConversationStatus = createAsyncThunk(
  'conversation/updateStatus',
  async ({ conversationId, status }: { conversationId: string; status: string }, { rejectWithValue }) => {
    try {
      const response = await conversationAPI.updateConversationStatus(conversationId, status);
      return response.data;
    } catch (error) {
      return rejectWithValue(error as APIError);
    }
  }
);

export const escalateConversation = createAsyncThunk(
  'conversation/escalate',
  async ({ conversationId, reason, priority = 'high' }: {
    conversationId: string;
    reason: string;
    priority?: string;
  }, { rejectWithValue }) => {
    try {
      const response = await conversationAPI.escalateConversation(conversationId, { reason, priority });
      return response.data;
    } catch (error) {
      return rejectWithValue(error as APIError);
    }
  }
);

// Initial state
const initialState: ConversationState = {
  conversations: [],
  currentConversation: null,
  messages: [],
  isLoading: false,
  error: null,
  hasMore: true,
  totalCount: 0,
  filters: {},
  sortBy: 'lastActivityAt',
  sortOrder: 'desc',
};

// Slice
export const conversationSlice = createSlice({
  name: 'conversation',
  initialState,
  reducers: {
    setConversations: (state, action: PayloadAction<Conversation[]>) => {
      state.conversations = action.payload;
    },
    
    addConversation: (state, action: PayloadAction<Conversation>) => {
      state.conversations.unshift(action.payload);
      state.totalCount += 1;
    },
    
    updateConversation: (state, action: PayloadAction<Conversation>) => {
      const index = state.conversations.findIndex(c => c.id === action.payload.id);
      if (index !== -1) {
        state.conversations[index] = action.payload;
      }
      if (state.currentConversation?.id === action.payload.id) {
        state.currentConversation = action.payload;
      }
    },
    
    removeConversation: (state, action: PayloadAction<string>) => {
      state.conversations = state.conversations.filter(c => c.id !== action.payload);
      state.totalCount -= 1;
      if (state.currentConversation?.id === action.payload) {
        state.currentConversation = null;
      }
    },
    
    setCurrentConversation: (state, action: PayloadAction<Conversation | null>) => {
      state.currentConversation = action.payload;
    },
    
    addMessage: (state, action: PayloadAction<Message>) => {
      state.messages.push(action.payload);
      if (state.currentConversation) {
        state.currentConversation.messageCount += 1;
        state.currentConversation.lastActivityAt = new Date().toISOString();
      }
    },
    
    updateMessage: (state, action: PayloadAction<Message>) => {
      const index = state.messages.findIndex(m => m.id === action.payload.id);
      if (index !== -1) {
        state.messages[index] = action.payload;
      }
    },
    
    setMessages: (state, action: PayloadAction<Message[]>) => {
      state.messages = action.payload;
    },
    
    clearMessages: (state) => {
      state.messages = [];
    },
    
    setFilters: (state, action: PayloadAction<FilterParams>) => {
      state.filters = action.payload;
    },
    
    clearFilters: (state) => {
      state.filters = {};
    },
    
    setSort: (state, action: PayloadAction<{ sortBy: string; sortOrder: 'asc' | 'desc' }>) => {
      state.sortBy = action.payload.sortBy;
      state.sortOrder = action.payload.sortOrder;
    },
    
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    
    clearError: (state) => {
      state.error = null;
    },
    
    updateTypingIndicator: (state, action: PayloadAction<{ conversationId: string; userId: string; userName: string; isTyping: boolean }>) => {
      // Handle typing indicators
      const { conversationId, userId, userName, isTyping } = action.payload;
      if (state.currentConversation?.id === conversationId) {
        // Update typing status in current conversation
        if (!state.currentConversation.metadata) {
          state.currentConversation.metadata = {};
        }
        state.currentConversation.metadata.typingUsers = state.currentConversation.metadata.typingUsers || {};
        
        if (isTyping) {
          state.currentConversation.metadata.typingUsers[userId] = {
            userId,
            userName,
            timestamp: new Date().toISOString(),
          };
        } else {
          delete state.currentConversation.metadata.typingUsers[userId];
        }
      }
    },
    
    updateSentiment: (state, action: PayloadAction<{ conversationId: string; sentiment: string; score: number }>) => {
      const { conversationId, sentiment, score } = action.payload;
      
      if (state.currentConversation?.id === conversationId) {
        state.currentConversation.sentimentCurrent = sentiment as any;
        state.currentConversation.metadata = {
          ...state.currentConversation.metadata,
          sentimentScore: score,
        };
      }
      
      const conversationIndex = state.conversations.findIndex(c => c.id === conversationId);
      if (conversationIndex !== -1) {
        state.conversations[conversationIndex].sentimentCurrent = sentiment as any;
      }
    },
    
    updateEmotion: (state, action: PayloadAction<{ conversationId: string; emotion: string; intensity: number }>) => {
      const { conversationId, emotion, intensity } = action.payload;
      
      if (state.currentConversation?.id === conversationId) {
        state.currentConversation.emotionCurrent = emotion as any;
        state.currentConversation.metadata = {
          ...state.currentConversation.metadata,
          emotionIntensity: intensity,
        };
      }
      
      const conversationIndex = state.conversations.findIndex(c => c.id === conversationId);
      if (conversationIndex !== -1) {
        state.conversations[conversationIndex].emotionCurrent = emotion as any;
      }
    },
  },
  
  extraReducers: (builder) => {
    builder
      // Fetch conversations
      .addCase(fetchConversations.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchConversations.fulfilled, (state, action) => {
        state.isLoading = false;
        state.conversations = action.payload.items;
        state.totalCount = action.payload.totalCount;
        state.hasMore = action.payload.hasMore;
      })
      .addCase(fetchConversations.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload?.message || 'Failed to fetch conversations';
      })
      
      // Fetch conversation
      .addCase(fetchConversation.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchConversation.fulfilled, (state, action) => {
        state.isLoading = false;
        state.currentConversation = action.payload;
        
        // Update in conversations list
        const index = state.conversations.findIndex(c => c.id === action.payload.id);
        if (index !== -1) {
          state.conversations[index] = action.payload;
        }
      })
      .addCase(fetchConversation.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload?.message || 'Failed to fetch conversation';
      })
      
      // Fetch messages
      .addCase(fetchMessages.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchMessages.fulfilled, (state, action) => {
        state.isLoading = false;
        state.messages = action.payload.messages;
      })
      .addCase(fetchMessages.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload?.message || 'Failed to fetch messages';
      })
      
      // Create conversation
      .addCase(createConversation.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(createConversation.fulfilled, (state, action) => {
        state.isLoading = false;
        state.conversations.unshift(action.payload);
        state.currentConversation = action.payload;
        state.totalCount += 1;
      })
      .addCase(createConversation.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload?.message || 'Failed to create conversation';
      })
      
      // Send message
      .addCase(sendMessage.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.isLoading = false;
        state.messages.push(action.payload);
        
        if (state.currentConversation) {
          state.currentConversation.messageCount += 1;
          state.currentConversation.lastActivityAt = new Date().toISOString();
        }
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload?.message || 'Failed to send message';
      })
      
      // Update conversation status
      .addCase(updateConversationStatus.fulfilled, (state, action) => {
        if (state.currentConversation?.id === action.payload.id) {
          state.currentConversation.status = action.payload.status;
        }
        
        const index = state.conversations.findIndex(c => c.id === action.payload.id);
        if (index !== -1) {
          state.conversations[index].status = action.payload.status;
        }
      })
      
      // Escalate conversation
      .addCase(escalateConversation.fulfilled, (state, action) => {
        if (state.currentConversation?.id === action.payload.id) {
          state.currentConversation.escalated = true;
          state.currentConversation.status = 'escalated';
        }
        
        const index = state.conversations.findIndex(c => c.id === action.payload.id);
        if (index !== -1) {
          state.conversations[index].escalated = true;
          state.conversations[index].status = 'escalated';
        }
      });
  },
});

// Selectors
export const selectConversation = (state: { conversation: ConversationState }) => state.conversation;
export const selectConversations = (state: { conversation: ConversationState }) => state.conversation.conversations;
export const selectCurrentConversation = (state: { conversation: ConversationState }) => state.conversation.currentConversation;
export const selectMessages = (state: { conversation: ConversationState }) => state.conversation.messages;
export const selectConversationLoading = (state: { conversation: ConversationState }) => state.conversation.isLoading;
export const selectConversationError = (state: { conversation: ConversationState }) => state.conversation.error;
export const selectHasMore = (state: { conversation: ConversationState }) => state.conversation.hasMore;
export const selectTotalCount = (state: { conversation: ConversationState }) => state.conversation.totalCount;
export const selectFilters = (state: { conversation: ConversationState }) => state.conversation.filters;
export const selectSort = (state: { conversation: ConversationState }) => ({
  sortBy: state.conversation.sortBy,
  sortOrder: state.conversation.sortOrder,
});

// Action creators
export const {
  setConversations,
  addConversation,
  updateConversation,
  removeConversation,
  setCurrentConversation,
  addMessage,
  updateMessage,
  setMessages,
  clearMessages,
  setFilters,
  clearFilters,
  setSort,
  setLoading,
  setError,
  clearError,
  updateTypingIndicator,
  updateSentiment,
  updateEmotion,
} = conversationSlice.actions;

export default conversationSlice.reducer;
```

## frontend/src/store/slices/uiSlice.ts
```typescript
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { UIState } from '../types';

// Initial state
const initialState: UIState = {
  theme: 'system',
  language: 'en',
  fontSize: 'medium',
  reducedMotion: false,
  highContrast: false,
  sidebarCollapsed: false,
  notifications: {
    enabled: true,
    sound: true,
    desktop: true,
    email: false,
    push: true,
  },
  accessibility: {
    keyboardNavigation: false,
    screenReaderAnnouncements: true,
    focusIndicators: true,
    skipLinks: true,
  },
  chat: {
    autoScroll: true,
    showTimestamps: true,
    showAvatars: true,
    compactMode: false,
    enterToSend: true,
  },
};

// Load initial state from localStorage
const loadInitialState = (): UIState => {
  try {
    const savedState = localStorage.getItem('ui-settings');
    if (savedState) {
      const parsed = JSON.parse(savedState);
      // Merge with initial state to ensure all properties exist
      return { ...initialState, ...parsed };
    }
  } catch (error) {
    console.error('Failed to load UI settings from localStorage:', error);
  }
  return initialState;
};

// Slice
export const uiSlice = createSlice({
  name: 'ui',
  initialState: loadInitialState(),
  reducers: {
    setTheme: (state, action: PayloadAction<'light' | 'dark' | 'system'>) => {
      state.theme = action.payload;
      saveToLocalStorage(state);
      
      // Apply theme immediately
      applyTheme(action.payload);
    },
    
    setLanguage: (state, action: PayloadAction<string>) => {
      state.language = action.payload;
      saveToLocalStorage(state);
      
      // Update document language
      document.documentElement.lang = action.payload;
      document.documentElement.dir = getLanguageDirection(action.payload);
    },
    
    setFontSize: (state, action: PayloadAction<'small' | 'medium' | 'large'>) => {
      state.fontSize = action.payload;
      saveToLocalStorage(state);
      
      // Apply font size
      applyFontSize(action.payload);
    },
    
    setReducedMotion: (state, action: PayloadAction<boolean>) => {
      state.reducedMotion = action.payload;
      saveToLocalStorage(state);
      
      // Apply reduced motion
      applyReducedMotion(action.payload);
    },
    
    setHighContrast: (state, action: PayloadAction<boolean>) => {
      state.highContrast = action.payload;
      saveToLocalStorage(state);
      
      // Apply high contrast
      applyHighContrast(action.payload);
    },
    
    toggleSidebar: (state) => {
      state.sidebarCollapsed = !state.sidebarCollapsed;
      saveToLocalStorage(state);
    },
    
    setSidebarCollapsed: (state, action: PayloadAction<boolean>) => {
      state.sidebarCollapsed = action.payload;
      saveToLocalStorage(state);
    },
    
    updateNotifications: (state, action: PayloadAction<Partial<UIState['notifications']>>) => {
      state.notifications = { ...state.notifications, ...action.payload };
      saveToLocalStorage(state);
    },
    
    updateAccessibility: (state, action: PayloadAction<Partial<UIState['accessibility']>>) => {
      state.accessibility = { ...state.accessibility, ...action.payload };
      saveToLocalStorage(state);
      
      // Apply accessibility settings
      applyAccessibilitySettings(state.accessibility);
    },
    
    updateChatSettings: (state, action: PayloadAction<Partial<UIState['chat']>>) => {
      state.chat = { ...state.chat, ...action.payload };
      saveToLocalStorage(state);
    },
    
    resetUISettings: () => {
      const defaultState = initialState;
      saveToLocalStorage(defaultState);
      applyAllSettings(defaultState);
      return defaultState;
    },
    
    loadUISettings: (state) => {
      const savedState = loadInitialState();
      Object.assign(state, savedState);
      applyAllSettings(savedState);
    },
  },
});

// Helper functions
const saveToLocalStorage = (state: UIState) => {
  try {
    localStorage.setItem('ui-settings', JSON.stringify(state));
  } catch (error) {
    console.error('Failed to save UI settings to localStorage:', error);
  }
};

const applyTheme = (theme: 'light' | 'dark' | 'system') => {
  const root = document.documentElement;
  const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  const effectiveTheme = theme === 'system' ? systemTheme : theme;
  
  root.setAttribute('data-theme', effectiveTheme);
  root.classList.toggle('dark', effectiveTheme === 'dark');
  
  // Dispatch custom event for theme change
  window.dispatchEvent(new CustomEvent('themechange', { detail: { theme: effectiveTheme } }));
};

const applyFontSize = (fontSize: 'small' | 'medium' | 'large') => {
  const root = document.documentElement;
  root.setAttribute('data-font-size', fontSize);
  
  // Apply CSS custom properties
  switch (fontSize) {
    case 'small':
      root.style.setProperty('--font-size-base', '0.875rem');
      root.style.setProperty('--line-height-base', '1.25rem');
      break;
    case 'large':
      root.style.setProperty('--font-size-base', '1.125rem');
      root.style.setProperty('--line-height-base', '1.75rem');
      break;
    default: // medium
      root.style.setProperty('--font-size-base', '1rem');
      root.style.setProperty('--line-height-base', '1.5rem');
  }
};

const applyReducedMotion = (reducedMotion: boolean) => {
  const root = document.documentElement;
  root.setAttribute('data-reduced-motion', reducedMotion.toString());
  
  if (reducedMotion) {
    root.style.setProperty('--transition-duration', '0.01ms');
    root.style.setProperty('--animation-duration', '0.01ms');
  } else {
    root.style.removeProperty('--transition-duration');
    root.style.removeProperty('--animation-duration');
  }
};

const applyHighContrast = (highContrast: boolean) => {
  const root = document.documentElement;
  root.setAttribute('data-high-contrast', highContrast.toString());
  
  if (highContrast) {
    root.classList.add('high-contrast');
  } else {
    root.classList.remove('high-contrast');
  }
};

const applyAccessibilitySettings = (settings: UIState['accessibility']) => {
  const root = document.documentElement;
  
  // Keyboard navigation
  if (settings.keyboardNavigation) {
    root.classList.add('keyboard-navigation');
    // Add keyboard event listeners
    document.addEventListener('keydown', handleKeyboardNavigation);
  } else {
    root.classList.remove('keyboard-navigation');
    document.removeEventListener('keydown', handleKeyboardNavigation);
  }
  
  // Focus indicators
  if (settings.focusIndicators) {
    root.classList.add('focus-indicators-visible');
  } else {
    root.classList.remove('focus-indicators-visible');
  }
  
  // Skip links
  if (settings.skipLinks) {
    createSkipLinks();
  } else {
    removeSkipLinks();
  }
};

const applyAllSettings = (state: UIState) => {
  applyTheme(state.theme);
  applyFontSize(state.fontSize);
  applyReducedMotion(state.reducedMotion);
  applyHighContrast(state.highContrast);
  applyAccessibilitySettings(state.accessibility);
  
  // Set document language and direction
  document.documentElement.lang = state.language;
  document.documentElement.dir = getLanguageDirection(state.language);
};

const getLanguageDirection = (language: string): 'ltr' | 'rtl' => {
  const rtlLanguages = ['ar', 'he', 'fa', 'ur'];
  return rtlLanguages.includes(language) ? 'rtl' : 'ltr';
};

const handleKeyboardNavigation = (event: KeyboardEvent) => {
  // Implement keyboard navigation logic
  if (event.key === 'Tab') {
    document.body.classList.add('keyboard-navigation-active');
  }
};

const createSkipLinks = () => {
  const skipLink = document.createElement('a');
  skipLink.href = '#main-content';
  skipLink.className = 'skip-link';
  skipLink.textContent = 'Skip to main content';
  document.body.insertBefore(skipLink, document.body.firstChild);
};

const removeSkipLinks = () => {
  const skipLinks = document.querySelectorAll('.skip-link');
  skipLinks.forEach(link => link.remove());
};

// System preference listeners
const setupSystemPreferenceListeners = () => {
  // Theme preference
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  mediaQuery.addEventListener('change', (e) => {
    const currentState = JSON.parse(localStorage.getItem('ui-settings') || '{}');
    if (currentState.theme === 'system') {
      applyTheme('system');
    }
  });
  
  // Reduced motion preference
  const reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  reducedMotionQuery.addEventListener('change', (e) => {
    const currentState = JSON.parse(localStorage.getItem('ui-settings') || '{}');
    if (currentState.reducedMotion !== e.matches) {
      // Update state to match system preference
      store.dispatch(setReducedMotion(e.matches));
    }
  });
  
  // High contrast preference
  const highContrastQuery = window.matchMedia('(prefers-contrast: high)');
  highContrastQuery.addEventListener('change', (e) => {
    const currentState = JSON.parse(localStorage.getItem('ui-settings') || '{}');
    if (currentState.highContrast !== e.matches) {
      // Update state to match system preference
      store.dispatch(setHighContrast(e.matches));
    }
  });
};

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
  setupSystemPreferenceListeners();
});

// Export store for use in helper functions
import { store } from '../index';

// Action creators
export const {
  setTheme,
  setLanguage,
  setFontSize,
  setReducedMotion,
  setHighContrast,
  toggleSidebar,
  setSidebarCollapsed,
  updateNotifications,
  updateAccessibility,
  updateChatSettings,
  resetUISettings,
  loadUISettings,
} = uiSlice.actions;

// Selectors
export const selectUI = (state: { ui: UIState }) => state.ui;
export const selectTheme = (state: { ui: UIState }) => state.ui.theme;
export const selectLanguage = (state: { ui: UIState }) => state.ui.language;
export const selectFontSize = (state: { ui: UIState }) => state.ui.fontSize;
export const selectReducedMotion = (state: { ui: UIState }) => state.ui.reducedMotion;
export const selectHighContrast = (state: { ui: UIState }) => state.ui.highContrast;
export const selectSidebarCollapsed = (state: { ui: UIState }) => state.ui.sidebarCollapsed;
export const selectNotifications = (state: { ui: UIState }) => state.ui.notifications;
export const selectAccessibility = (state: { ui: UIState }) => state.ui.accessibility;
export const selectChatSettings = (state: { ui: UIState }) => state.ui.chat;

export default uiSlice.reducer;
```

https://www.kimi.com/share/d2ulg5d7vds29nctpli0
