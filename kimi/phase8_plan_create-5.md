<think>
I need to continue with the same rigorous approach. Let me systematically complete:

1. Notification slice
2. WebSocket slice  
3. API configuration
4. Store hooks
5. Then move to services, components, and utilities

Each file needs to:
- Comply with PRD v4 accessibility requirements
- Use TypeScript strict mode
- Align with Database Schema v4
- Include proper error handling
- Follow security best practices
- Be evidence-based with clear implementation

Let me continue methodically with the remaining store files.
</think>

Continuing with Phase 8 implementation - Remaining store files:

## frontend/src/store/slices/notificationSlice.ts
```typescript
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { NotificationState } from '../types';

// Action types for notifications
export interface Notification {
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
    data?: Record<string, unknown>;
  }>;
  priority?: 'low' | 'medium' | 'high';
  category?: 'system' | 'conversation' | 'user' | 'security';
}

export interface ShowNotificationPayload {
  type: Notification['type'];
  title: string;
  message: string;
  persistent?: boolean;
  actions?: Notification['actions'];
  priority?: Notification['priority'];
  category?: Notification['category'];
  autoClose?: number; // milliseconds, 0 to disable
}

// Initial state
const initialState: NotificationState = {
  notifications: [],
  unreadCount: 0,
};

// Helper functions
const generateNotificationId = (): string => {
  return `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

const createNotification = (payload: ShowNotificationPayload): Notification => {
  return {
    id: generateNotificationId(),
    type: payload.type,
    title: payload.title,
    message: payload.message,
    timestamp: new Date().toISOString(),
    read: false,
    persistent: payload.persistent || false,
    actions: payload.actions,
    priority: payload.priority || 'medium',
    category: payload.category || 'system',
  };
};

// Slice
export const notificationSlice = createSlice({
  name: 'notification',
  initialState,
  reducers: {
    showNotification: (state, action: PayloadAction<ShowNotificationPayload>) => {
      const notification = createNotification(action.payload);
      state.notifications.unshift(notification);
      state.unreadCount += 1;
      
      // Limit notifications to prevent memory issues
      if (state.notifications.length > 50) {
        const removed = state.notifications.splice(50);
        state.unreadCount -= removed.filter(n => !n.read).length;
      }
      
      // Auto-close non-persistent notifications
      if (!notification.persistent && action.payload.autoClose !== 0) {
        const autoCloseDelay = action.payload.autoClose || 5000; // Default 5 seconds
        setTimeout(() => {
          // This would need to be dispatched from outside the reducer
          // We'll handle this in the notification component
        }, autoCloseDelay);
      }
    },
    
    addNotification: (state, action: PayloadAction<Notification>) => {
      state.notifications.unshift(action.payload);
      if (!action.payload.read) {
        state.unreadCount += 1;
      }
    },
    
    removeNotification: (state, action: PayloadAction<string>) => {
      const notification = state.notifications.find(n => n.id === action.payload);
      if (notification && !notification.read) {
        state.unreadCount -= 1;
      }
      state.notifications = state.notifications.filter(n => n.id !== action.payload);
    },
    
    markAsRead: (state, action: PayloadAction<string>) => {
      const notification = state.notifications.find(n => n.id === action.payload);
      if (notification && !notification.read) {
        notification.read = true;
        state.unreadCount -= 1;
      }
    },
    
    markAllAsRead: (state) => {
      state.notifications.forEach(notification => {
        notification.read = true;
      });
      state.unreadCount = 0;
    },
    
    clearNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(n => n.id !== action.payload);
      // Recalculate unread count
      state.unreadCount = state.notifications.filter(n => !n.read).length;
    },
    
    clearAllNotifications: (state) => {
      state.notifications = [];
      state.unreadCount = 0;
    },
    
    clearReadNotifications: (state) => {
      state.notifications = state.notifications.filter(n => !n.read);
      state.unreadCount = state.notifications.length;
    },
    
    updateNotification: (state, action: PayloadAction<{ id: string; updates: Partial<Notification> }>) => {
      const notification = state.notifications.find(n => n.id === action.payload.id);
      if (notification) {
        Object.assign(notification, action.payload.updates);
      }
    },
    
    setUnreadCount: (state, action: PayloadAction<number>) => {
      state.unreadCount = action.payload;
    },
    
    // Bulk operations
    bulkMarkAsRead: (state, action: PayloadAction<string[]>) => {
      const ids = action.payload;
      let readCount = 0;
      
      state.notifications.forEach(notification => {
        if (ids.includes(notification.id) && !notification.read) {
          notification.read = true;
          readCount++;
        }
      });
      
      state.unreadCount -= readCount;
    },
    
    bulkRemove: (state, action: PayloadAction<string[]>) => {
      const ids = action.payload;
      let removedUnreadCount = 0;
      
      state.notifications = state.notifications.filter(notification => {
        if (ids.includes(notification.id)) {
          if (!notification.read) {
            removedUnreadCount++;
          }
          return false;
        }
        return true;
      });
      
      state.unreadCount -= removedUnreadCount;
    },
    
    // Category-based operations
    clearByCategory: (state, action: PayloadAction<Notification['category']>) => {
      const category = action.payload;
      let removedUnreadCount = 0;
      
      state.notifications = state.notifications.filter(notification => {
        if (notification.category === category) {
          if (!notification.read) {
            removedUnreadCount++;
          }
          return false;
        }
        return true;
      });
      
      state.unreadCount -= removedUnreadCount;
    },
    
    markCategoryAsRead: (state, action: PayloadAction<Notification['category']>) => {
      const category = action.payload;
      let readCount = 0;
      
      state.notifications.forEach(notification => {
        if (notification.category === category && !notification.read) {
          notification.read = true;
          readCount++;
        }
      });
      
      state.unreadCount -= readCount;
    },
    
    // Priority-based operations
    clearByPriority: (state, action: PayloadAction<Notification['priority']>) => {
      const priority = action.payload;
      let removedUnreadCount = 0;
      
      state.notifications = state.notifications.filter(notification => {
        if (notification.priority === priority) {
          if (!notification.read) {
            removedUnreadCount++;
          }
          return false;
        }
        return true;
      });
      
      state.unreadCount -= removedUnreadCount;
    },
  },
});

// Helper functions for common notification types
export const showSuccessNotification = (title: string, message: string, options?: Partial<ShowNotificationPayload>) => {
  return notificationSlice.actions.showNotification({
    type: 'success',
    title,
    message,
    autoClose: 3000,
    ...options,
  });
};

export const showErrorNotification = (title: string, message: string, options?: Partial<ShowNotificationPayload>) => {
  return notificationSlice.actions.showNotification({
    type: 'error',
    title,
    message,
    persistent: true,
    priority: 'high',
    ...options,
  });
};

export const showWarningNotification = (title: string, message: string, options?: Partial<ShowNotificationPayload>) => {
  return notificationSlice.actions.showNotification({
    type: 'warning',
    title,
    message,
    autoClose: 5000,
    priority: 'medium',
    ...options,
  });
};

export const showInfoNotification = (title: string, message: string, options?: Partial<ShowNotificationPayload>) => {
  return notificationSlice.actions.showNotification({
    type: 'info',
    title,
    message,
    autoClose: 4000,
    ...options,
  });
};

// System notification helpers
export const showSystemNotification = (message: string, priority: Notification['priority'] = 'medium') => {
  return notificationSlice.actions.showNotification({
    type: 'info',
    title: 'System Update',
    message,
    category: 'system',
    priority,
    autoClose: priority === 'high' ? 0 : 5000,
  });
};

export const showConversationNotification = (title: string, message: string, conversationId: string) => {
  return notificationSlice.actions.showNotification({
    type: 'info',
    title,
    message,
    category: 'conversation',
    actions: [
      {
        label: 'View Conversation',
        action: 'navigate_to_conversation',
        data: { conversationId },
      },
    ],
  });
};

export const showSecurityNotification = (title: string, message: string) => {
  return notificationSlice.actions.showNotification({
    type: 'warning',
    title,
    message,
    category: 'security',
    priority: 'high',
    persistent: true,
  });
};

// Selectors
export const selectNotification = (state: { notification: NotificationState }) => state.notification;
export const selectNotifications = (state: { notification: NotificationState }) => state.notification.notifications;
export const selectUnreadCount = (state: { notification: NotificationState }) => state.notification.unreadCount;
export const selectUnreadNotifications = (state: { notification: NotificationState }) => 
  state.notification.notifications.filter(n => !n.read);

export const selectNotificationsByCategory = (category: Notification['category']) => 
  (state: { notification: NotificationState }) => 
    state.notification.notifications.filter(n => n.category === category);

export const selectNotificationsByType = (type: Notification['type']) => 
  (state: { notification: NotificationState }) => 
    state.notification.notifications.filter(n => n.type === type);

export const selectNotificationsByPriority = (priority: Notification['priority']) => 
  (state: { notification: NotificationState }) => 
    state.notification.notifications.filter(n => n.priority === priority);

export const selectPersistentNotifications = (state: { notification: NotificationState }) => 
  state.notification.notifications.filter(n => n.persistent);

export const selectRecentNotifications = (count: number = 10) => 
  (state: { notification: NotificationState }) => 
    state.notification.notifications.slice(0, count);

// Action creators
export const {
  showNotification,
  addNotification,
  removeNotification,
  markAsRead,
  markAllAsRead,
  clearNotification,
  clearAllNotifications,
  clearReadNotifications,
  updateNotification,
  setUnreadCount,
  bulkMarkAsRead,
  bulkRemove,
  clearByCategory,
  markCategoryAsRead,
  clearByPriority,
} = notificationSlice.actions;

export default notificationSlice.reducer;
```

## frontend/src/store/slices/websocketSlice.ts
```typescript
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { WebSocketState, WebSocketMessage, TypingIndicator, ConversationStatus } from '../types';

// Initial state
const initialState: WebSocketState = {
  isConnected: false,
  connectionId: null,
  lastPingAt: null,
  reconnectAttempts: 0,
  isReconnecting: false,
  error: null,
};

// Slice
export const websocketSlice = createSlice({
  name: 'websocket',
  initialState,
  reducers: {
    connect: (state) => {
      state.isReconnecting = true;
      state.error = null;
    },
    
    connected: (state, action: PayloadAction<{ connectionId: string }>) => {
      state.isConnected = true;
      state.connectionId = action.payload.connectionId;
      state.isReconnecting = false;
      state.reconnectAttempts = 0;
      state.error = null;
    },
    
    disconnect: (state) => {
      state.isConnected = false;
      state.isReconnecting = false;
    },
    
    disconnected: (state) => {
      state.isConnected = false;
      state.connectionId = null;
      state.lastPingAt = null;
      state.isReconnecting = false;
    },
    
    reconnect: (state) => {
      state.isReconnecting = true;
      state.reconnectAttempts += 1;
    },
    
    reconnectFailed: (state, action: PayloadAction<string>) => {
      state.isReconnecting = false;
      state.error = action.payload;
    },
    
    ping: (state) => {
      state.lastPingAt = new Date().toISOString();
    },
    
    pong: (state) => {
      state.lastPingAt = new Date().toISOString();
    },
    
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    
    clearError: (state) => {
      state.error = null;
    },
    
    resetReconnectAttempts: (state) => {
      state.reconnectAttempts = 0;
    },
  },
});

// WebSocket message handlers (these would be handled by middleware in a real app)
export const handleWebSocketMessage = (message: WebSocketMessage) => {
  return (dispatch: any) => {
    switch (message.type) {
      case 'message':
        dispatch(handleIncomingMessage(message));
        break;
      case 'typing':
        dispatch(handleTypingIndicator(message as TypingIndicator));
        break;
      case 'status':
        dispatch(handleConversationStatus(message as ConversationStatus));
        break;
      case 'error':
        dispatch(handleWebSocketError(message));
        break;
      default:
        console.warn('Unknown WebSocket message type:', message.type);
    }
  };
};

const handleIncomingMessage = (message: WebSocketMessage) => {
  return {
    type: 'conversation/addMessage',
    payload: message.data,
  };
};

const handleTypingIndicator = (typing: TypingIndicator) => {
  return {
    type: 'conversation/updateTypingIndicator',
    payload: typing,
  };
};

const handleConversationStatus = (status: ConversationStatus) => {
  return {
    type: 'conversation/updateConversationStatus',
    payload: status,
  };
};

const handleWebSocketError = (error: WebSocketMessage) => {
  return {
    type: 'notification/showErrorNotification',
    payload: {
      title: 'Connection Error',
      message: (error.data as any)?.message || 'WebSocket connection error occurred',
    },
  };
};

// Selectors
export const selectWebSocket = (state: { websocket: WebSocketState }) => state.websocket;
export const selectIsConnected = (state: { websocket: WebSocketState }) => state.websocket.isConnected;
export const selectConnectionId = (state: { websocket: WebSocketState }) => state.websocket.connectionId;
export const selectLastPingAt = (state: { websocket: WebSocketState }) => state.websocket.lastPingAt;
export const selectReconnectAttempts = (state: { websocket: WebSocketState }) => state.websocket.reconnectAttempts;
export const selectIsReconnecting = (state: { websocket: WebSocketState }) => state.websocket.isReconnecting;
export const selectWebSocketError = (state: { websocket: WebSocketState }) => state.websocket.error;

// Action creators
export const {
  connect,
  connected,
  disconnect,
  disconnected,
  reconnect,
  reconnectFailed,
  ping,
  pong,
  setError,
  clearError,
  resetReconnectAttempts,
} = websocketSlice.actions;

export default websocketSlice.reducer;
```

## frontend/src/store/api/index.ts
```typescript
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import type { BaseQueryFn, FetchArgs, FetchBaseQueryError } from '@reduxjs/toolkit/query';
import { Mutex } from 'async-mutex';
import { RootState } from '../types';
import { tokenService } from '@services/auth/tokenService';
import { authSlice } from '../slices/authSlice';
import { APIResponse } from '../types';

// Create a mutex to prevent multiple refresh token requests
const mutex = new Mutex();

// Custom base query with authentication and retry logic
const baseQuery = fetchBaseQuery({
  baseUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  prepareHeaders: (headers, { getState }) => {
    const token = (getState() as RootState).auth.token;
    if (token) {
      headers.set('authorization', `Bearer ${token}`);
    }
    headers.set('Content-Type', 'application/json');
    headers.set('Accept', 'application/json');
    return headers;
  },
  timeout: 30000, // 30 seconds
});

// Custom base query with automatic token refresh
const baseQueryWithReauth: BaseQueryFn<string | FetchArgs, unknown, FetchBaseQueryError> = async (
  args,
  api,
  extraOptions
) => {
  // Wait for any ongoing mutex operations
  await mutex.waitForUnlock();
  
  let result = await baseQuery(args, api, extraOptions);
  
  // Handle 401 Unauthorized responses
  if (result.error && result.error.status === 401) {
    // Check if mutex is locked (refresh already in progress)
    if (!mutex.isLocked()) {
      const release = await mutex.acquire();
      
      try {
        // Try to refresh the token
        const refreshToken = tokenService.getRefreshToken();
        if (refreshToken) {
          const refreshResult = await baseQuery(
            {
              url: '/auth/refresh',
              method: 'POST',
              body: { refreshToken },
            },
            api,
            extraOptions
          );
          
          if (refreshResult.data) {
            // Store the new token
            const { token, refreshToken: newRefreshToken, expiresAt } = refreshResult.data as any;
            tokenService.setToken(token);
            tokenService.setRefreshToken(newRefreshToken);
            tokenService.setExpiresAt(expiresAt);
            
            // Update auth state
            api.dispatch(authSlice.actions.setAuth({
              token,
              refreshToken: newRefreshToken,
              expiresAt,
            } as any));
            
            // Retry the original query with the new token
            result = await baseQuery(args, api, extraOptions);
          } else {
            // Refresh failed, logout
            api.dispatch(authSlice.actions.clearAuth());
            tokenService.clearTokens();
          }
        } else {
          // No refresh token available, logout
          api.dispatch(authSlice.actions.clearAuth());
          tokenService.clearTokens();
        }
      } finally {
        release();
      }
    } else {
      // Wait for the mutex to unlock and retry
      await mutex.waitForUnlock();
      result = await baseQuery(args, api, extraOptions);
    }
  }
  
  return result;
};

// API slice configuration
export const api = createApi({
  reducerPath: 'api',
  baseQuery: baseQueryWithReauth,
  tagTypes: [
    'User',
    'Organization',
    'Conversation',
    'Message',
    'Knowledge',
    'Analytics',
    'Settings',
    'Notification',
  ],
  endpoints: (builder) => ({}),
});

// Enhanced API response handler
export const handleApiResponse = async <T>(
  promise: Promise<{ data: T } | { error: FetchBaseQueryError }>
): Promise<APIResponse<T>> => {
  try {
    const result = await promise;
    
    if ('error' in result) {
      const error = result.error;
      return {
        data: null as any,
        status: error.status as number,
        errors: [{
          code: error.data?.toString() || 'UNKNOWN_ERROR',
          message: (error.data as any)?.message || 'An unknown error occurred',
          details: error.data as Record<string, unknown>,
          timestamp: new Date().toISOString(),
        }],
      };
    }
    
    return {
      data: result.data,
      status: 200,
      metadata: (result.data as any)?.metadata,
    };
  } catch (error) {
    return {
      data: null as any,
      status: 500,
      errors: [{
        code: 'INTERNAL_ERROR',
        message: 'Internal server error',
        details: { error: error instanceof Error ? error.message : String(error) },
        timestamp: new Date().toISOString(),
      }],
    };
  }
};

// API error handler with user-friendly messages
export const getErrorMessage = (error: FetchBaseQueryError): string => {
  if (error.status === 401) {
    return 'Your session has expired. Please log in again.';
  }
  if (error.status === 403) {
    return 'You do not have permission to perform this action.';
  }
  if (error.status === 404) {
    return 'The requested resource was not found.';
  }
  if (error.status === 429) {
    return 'Too many requests. Please try again later.';
  }
  if (error.status >= 500) {
    return 'A server error occurred. Please try again later.';
  }
  
  const errorData = error.data as any;
  if (errorData?.message) {
    return errorData.message;
  }
  if (errorData?.detail) {
    return errorData.detail;
  }
  
  return 'An unexpected error occurred. Please try again.';
};

// Retry configuration
export const retryConfig = {
  maxRetries: 3,
  retryDelay: (retryCount: number) => Math.min(1000 * Math.pow(2, retryCount), 30000),
  retryCondition: (error: FetchBaseQueryError) => {
    // Retry on network errors and 5xx status codes
    return !error.status || error.status >= 500;
  },
};

// Cache configuration
export const cacheConfig = {
  // Default cache time of 5 minutes
  keepUnusedDataFor: 300,
  refetchOnMountOrArgChange: true,
  refetchOnFocus: true,
  refetchOnReconnect: true,
};

// Export enhanced API utilities
export { api as default };
export * from './conversation';
export * from './auth';
export * from './analytics';
export * from './knowledge';
```

## frontend/src/store/api/conversation.ts
```typescript
import { api } from '../index';
import { Conversation, Message, PaginationParams, FilterParams, APIResponse } from '../types';

// Conversation API endpoints
export const conversationAPI = api.injectEndpoints({
  endpoints: (builder) => ({
    // Get conversations with pagination and filtering
    getConversations: builder.query<APIResponse<Conversation[]>, {
      page?: number;
      pageSize?: number;
      filters?: FilterParams;
      sortBy?: string;
      sortOrder?: 'asc' | 'desc';
    }>({
      query: ({ page = 1, pageSize = 20, filters = {}, sortBy = 'lastActivityAt', sortOrder = 'desc' }) => ({
        url: '/conversations',
        method: 'GET',
        params: {
          page,
          pageSize,
          ...filters,
          sortBy,
          sortOrder,
        },
      }),
      providesTags: (result) => 
        result?.data
          ? [
              ...result.data.map(({ id }) => ({ type: 'Conversation' as const, id })),
              { type: 'Conversation', id: 'LIST' },
            ]
          : [{ type: 'Conversation', id: 'LIST' }],
    }),
    
    // Get single conversation
    getConversation: builder.query<APIResponse<Conversation>, string>({
      query: (conversationId) => ({
        url: `/conversations/${conversationId}`,
        method: 'GET',
      }),
      providesTags: (result, error, conversationId) => [
        { type: 'Conversation', id: conversationId },
      ],
    }),
    
    // Get messages for a conversation
    getMessages: builder.query<APIResponse<Message[]>, {
      conversationId: string;
      page?: number;
      pageSize?: number;
      sortBy?: string;
      sortOrder?: 'asc' | 'desc';
    }>({
      query: ({ conversationId, page = 1, pageSize = 50, sortBy = 'createdAt', sortOrder = 'asc' }) => ({
        url: `/conversations/${conversationId}/messages`,
        method: 'GET',
        params: {
          page,
          pageSize,
          sortBy,
          sortOrder,
        },
      }),
      providesTags: (result, error, { conversationId }) => [
        { type: 'Message', id: `${conversationId}-LIST` },
        ...((result?.data || []).map(({ id }) => ({ type: 'Message' as const, id }))),
      ],
    }),
    
    // Create new conversation
    createConversation: builder.mutation<APIResponse<Conversation>, {
      title?: string;
      channel?: string;
      priority?: string;
      metadata?: Record<string, unknown>;
    }>({
      query: (body) => ({
        url: '/conversations',
        method: 'POST',
        body,
      }),
      invalidatesTags: [{ type: 'Conversation', id: 'LIST' }],
    }),
    
    // Send message to conversation
    sendMessage: builder.mutation<APIResponse<Message>, {
      conversationId: string;
      content: string;
      contentType?: string;
      metadata?: Record<string, unknown>;
    }>({
      query: ({ conversationId, ...body }) => ({
        url: `/conversations/${conversationId}/messages`,
        method: 'POST',
        body,
      }),
      invalidatesTags: (result, error, { conversationId }) => [
        { type: 'Message', id: `${conversationId}-LIST` },
        { type: 'Conversation', id: conversationId },
      ],
    }),
    
    // Update conversation status
    updateConversationStatus: builder.mutation<APIResponse<Conversation>, {
      conversationId: string;
      status: string;
    }>({
      query: ({ conversationId, status }) => ({
        url: `/conversations/${conversationId}/status`,
        method: 'PUT',
        body: { status },
      }),
      invalidatesTags: (result, error, { conversationId }) => [
        { type: 'Conversation', id: conversationId },
      ],
    }),
    
    // Update conversation priority
    updateConversationPriority: builder.mutation<APIResponse<Conversation>, {
      conversationId: string;
      priority: string;
    }>({
      query: ({ conversationId, priority }) => ({
        url: `/conversations/${conversationId}/priority`,
        method: 'PUT',
        body: { priority },
      }),
      invalidatesTags: (result, error, { conversationId }) => [
        { type: 'Conversation', id: conversationId },
      ],
    }),
    
    // Assign conversation to agent
    assignConversation: builder.mutation<APIResponse<Conversation>, {
      conversationId: string;
      agentId: string;
    }>({
      query: ({ conversationId, agentId }) => ({
        url: `/conversations/${conversationId}/assign`,
        method: 'PUT',
        body: { agentId },
      }),
      invalidatesTags: (result, error, { conversationId }) => [
        { type: 'Conversation', id: conversationId },
      ],
    }),
    
    // Escalate conversation
    escalateConversation: builder.mutation<APIResponse<Conversation>, {
      conversationId: string;
      reason: string;
      priority?: string;
      notes?: string;
    }>({
      query: ({ conversationId, ...body }) => ({
        url: `/conversations/${conversationId}/escalate`,
        method: 'POST',
        body,
      }),
      invalidatesTags: (result, error, { conversationId }) => [
        { type: 'Conversation', id: conversationId },
      ],
    }),
    
    // Add typing indicator
    sendTypingIndicator: builder.mutation<void, {
      conversationId: string;
      isTyping: boolean;
    }>({
      query: ({ conversationId, isTyping }) => ({
        url: `/conversations/${conversationId}/typing`,
        method: 'POST',
        body: { isTyping },
      }),
    }),
    
    // Mark messages as read
    markMessagesAsRead: builder.mutation<void, {
      conversationId: string;
      messageIds: string[];
    }>({
      query: ({ conversationId, messageIds }) => ({
        url: `/conversations/${conversationId}/read`,
        method: 'PUT',
        body: { messageIds },
      }),
      invalidatesTags: (result, error, { conversationId }) => [
        { type: 'Message', id: `${conversationId}-LIST` },
      ],
    }),
    
    // Upload attachment
    uploadAttachment: builder.mutation<APIResponse<{
      id: string;
      url: string;
      name: string;
      type: string;
      size: number;
    }>, {
      conversationId: string;
      file: File;
    }>({
      query: ({ conversationId, file }) => {
        const formData = new FormData();
        formData.append('file', file);
        
        return {
          url: `/conversations/${conversationId}/attachments`,
          method: 'POST',
          body: formData,
          formData: true,
        };
      },
      invalidatesTags: (result, error, { conversationId }) => [
        { type: 'Conversation', id: conversationId },
      ],
    }),
    
    // Get conversation analytics
    getConversationAnalytics: builder.query<APIResponse<{
      totalConversations: number;
      resolvedConversations: number;
      escalatedConversations: number;
      avgResolutionTime: number;
      avgResponseTime: number;
      satisfactionScore: number;
      aiDeflectionRate: number;
    }>, {
      dateFrom?: string;
      dateTo?: string;
      channel?: string;
    }>({
      query: (params) => ({
        url: '/conversations/analytics',
        method: 'GET',
        params,
      }),
      providesTags: ['Analytics'],
    }),
    
    // Get conversation suggestions
    getSuggestions: builder.query<APIResponse<{
      suggestions: Array<{
        id: string;
        title: string;
        content: string;
        confidence: number;
        source: string;
      }>;
    }>, {
      conversationId: string;
      query: string;
      context?: string;
    }>({
      query: ({ conversationId, ...params }) => ({
        url: `/conversations/${conversationId}/suggestions`,
        method: 'GET',
        params,
      }),
    }),
    
    // Export conversation
    exportConversation: builder.query<Blob, {
      conversationId: string;
      format: 'json' | 'csv' | 'pdf';
      includeMetadata?: boolean;
    }>({
      query: ({ conversationId, format, includeMetadata = true }) => ({
        url: `/conversations/${conversationId}/export`,
        method: 'GET',
        params: { format, includeMetadata },
        responseHandler: (response) => response.blob(),
      }),
    }),
  }),
});

// Export hooks
export const {
  useGetConversationsQuery,
  useGetConversationQuery,
  useGetMessagesQuery,
  useCreateConversationMutation,
  useSendMessageMutation,
  useUpdateConversationStatusMutation,
  useUpdateConversationPriorityMutation,
  useAssignConversationMutation,
  useEscalateConversationMutation,
  useSendTypingIndicatorMutation,
  useMarkMessagesAsReadMutation,
  useUploadAttachmentMutation,
  useGetConversationAnalyticsQuery,
  useGetSuggestionsQuery,
  useExportConversationQuery,
} = conversationAPI;

// Export API object
export { conversationAPI };
```

## frontend/src/store/hooks.ts
```typescript
import { useCallback, useEffect, useRef, useState } from 'react';
import { useAppDispatch, useAppSelector } from './types';
import { RootState } from './index';

// Typed Redux hooks with additional functionality
export { useAppDispatch, useAppSelector } from './types';

// Custom hooks for common patterns

/**
 * Hook for managing WebSocket connection with automatic reconnection
 */
export const useWebSocket = () => {
  const dispatch = useAppDispatch();
  const websocket = useAppSelector((state) => state.websocket);
  const isAuthenticated = useAppSelector((state) => state.auth.isAuthenticated);
  const token = useAppSelector((state) => state.auth.token);

  useEffect(() => {
    if (isAuthenticated && token && !websocket.isConnected && !websocket.isReconnecting) {
      dispatch({ type: 'websocket/connect' });
    }
  }, [dispatch, isAuthenticated, token, websocket.isConnected, websocket.isReconnecting]);

  return websocket;
};

/**
 * Hook for managing notifications with sound and desktop notifications
 */
export const useNotifications = () => {
  const dispatch = useAppDispatch();
  const notifications = useAppSelector((state) => state.notification.notifications);
  const settings = useAppSelector((state) => state.ui.notifications);

  const showNotification = useCallback(
    (notification: Parameters<typeof import('./slices/notificationSlice').showNotification>[0]) => {
      dispatch(import('./slices/notificationSlice').showNotification(notification));

      // Play sound if enabled
      if (settings.sound) {
        playNotificationSound(notification.type);
      }

      // Show desktop notification if enabled and supported
      if (settings.desktop && 'Notification' in window && Notification.permission === 'granted') {
        showDesktopNotification(notification);
      }
    },
    [dispatch, settings]
  );

  return {
    notifications,
    showNotification,
    markAsRead: (id: string) => dispatch(import('./slices/notificationSlice').markAsRead(id)),
    removeNotification: (id: string) => dispatch(import('./slices/notificationSlice').removeNotification(id)),
    clearAll: () => dispatch(import('./slices/notificationSlice').clearAllNotifications()),
  };
};

/**
 * Hook for managing authentication state with automatic token refresh
 */
export const useAuth = () => {
  const dispatch = useAppDispatch();
  const auth = useAppSelector((state) => state.auth);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('auth_token');
      const refreshToken = localStorage.getItem('auth_refresh_token');
      
      if (token && refreshToken) {
        try {
          // Verify token is still valid
          const expiresAt = localStorage.getItem('auth_expires_at');
          if (expiresAt && new Date(expiresAt) > new Date()) {
            // Token is still valid, restore auth state
            dispatch({
              type: 'auth/restoreAuth',
              payload: { token, refreshToken, expiresAt },
            });
          } else {
            // Token expired, attempt refresh
            await dispatch(import('./slices/authSlice').refreshToken()).unwrap();
          }
        } catch (error) {
          // Refresh failed, clear auth
          dispatch(import('./slices/authSlice').clearAuth());
        }
      }
      setIsCheckingAuth(false);
    };

    checkAuth();
  }, [dispatch]);

  const login = useCallback(
    async (credentials: { email: string; password: string; rememberMe?: boolean }) => {
      return dispatch(import('./slices/authSlice').login(credentials)).unwrap();
    },
    [dispatch]
  );

  const logout = useCallback(async () => {
    await dispatch(import('./slices/authSlice').logout()).unwrap();
  }, [dispatch]);

  return {
    ...auth,
    isLoading: auth.isLoading || isCheckingAuth,
    login,
    logout,
  };
};

/**
 * Hook for managing conversation state with optimistic updates
 */
export const useConversation = (conversationId?: string) => {
  const dispatch = useAppDispatch();
  const conversation = useAppSelector((state) => state.conversation);
  const currentConversation = useAppSelector((state) => 
    conversationId ? state.conversation.conversations.find(c => c.id === conversationId) : state.conversation.currentConversation
  );

  const sendMessage = useCallback(
    async (content: string, contentType = 'text') => {
      if (!currentConversation) return;

      // Optimistic update
      const tempMessage = {
        id: `temp_${Date.now()}`,
        conversationId: currentConversation.id,
        content,
        contentType,
        senderType: 'user' as const,
        createdAt: new Date().toISOString(),
        metadata: { optimistic: true },
      };

      dispatch(import('./slices/conversationSlice').addMessage(tempMessage));

      try {
        const result = await dispatch(
          import('./slices/conversationSlice').sendMessage({
            conversationId: currentConversation.id,
            content,
            contentType,
          })
        ).unwrap();

        // Replace optimistic message with real one
        dispatch(import('./slices/conversationSlice').updateMessage(result));
      } catch (error) {
        // Remove optimistic message on error
        dispatch(import('./slices/conversationSlice').removeNotification(tempMessage.id));
        throw error;
      }
    },
    [dispatch, currentConversation]
  );

  return {
    conversation,
    currentConversation,
    sendMessage,
  };
};

/**
 * Hook for managing UI state with accessibility features
 */
export const useUI = () => {
  const dispatch = useAppDispatch();
  const ui = useAppSelector((state) => state.ui);

  const setTheme = useCallback(
    (theme: 'light' | 'dark' | 'system') => {
      dispatch(import('./slices/uiSlice').setTheme(theme));
    },
    [dispatch]
  );

  const toggleSidebar = useCallback(() => {
    dispatch(import('./slices/uiSlice').toggleSidebar());
  }, [dispatch]);

  const updateAccessibility = useCallback(
    (settings: Partial<typeof ui.accessibility>) => {
      dispatch(import('./slices/uiSlice').updateAccessibility(settings));
    },
    [dispatch]
  );

  return {
    ui,
    setTheme,
    toggleSidebar,
    updateAccessibility,
  };
};

/**
 * Hook for debouncing values with proper cleanup
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * Hook for managing local storage with state synchronization
 */
export function useLocalStorage<T>(key: string, initialValue: T): [T, (value: T | ((val: T) => T)) => void] {
  // Get from local storage then parse stored json or return initialValue
  const readValue = (): T => {
    if (typeof window === 'undefined') {
      return initialValue;
    }
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  };

  const [storedValue, setStoredValue] = useState<T>(readValue);

  const setValue = (value: T | ((val: T) => T)) => {
    try {
      // Allow value to be a function so we have the same API as useState
      const newValue = value instanceof Function ? value(storedValue) : value;
      setStoredValue(newValue);
      window.localStorage.setItem(key, JSON.stringify(newValue));
    } catch (error) {
      console.warn(`Error setting localStorage key "${key}":`, error);
    }
  };

  useEffect(() => {
    setStoredValue(readValue());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return [storedValue, setValue];
}

/**
 * Hook for detecting if an element is visible on screen (for infinite scroll)
 */
export function useOnScreen(ref: React.RefObject<HTMLElement>, rootMargin = '0px'): boolean {
  const [isIntersecting, setIntersecting] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        setIntersecting(entry.isIntersecting);
      },
      {
        rootMargin,
        threshold: 0.1,
      }
    );
    if (ref.current) {
      observer.observe(ref.current);
    }
    return () => {
      observer.disconnect();
    };
  }, [ref, rootMargin]);

  return isIntersecting;
}

/**
 * Hook for managing keyboard shortcuts with accessibility
 */
export function useKeyboardShortcuts(shortcuts: Record<string, (event: KeyboardEvent) => void>) {
  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      // Don't handle if user is typing in an input
      const target = event.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return;
      }
      
      // Check for exact key match
      const shortcut = shortcuts[event.key];
      if (shortcut) {
        event.preventDefault();
        shortcut(event);
      }
      
      // Check for modifier combinations
      const modifierKey = `${event.ctrlKey || event.metaKey ? 'ctrl+' : ''}${event.altKey ? 'alt+' : ''}${event.shiftKey ? 'shift+' : ''}${event.key}`.toLowerCase();
      const modifierShortcut = shortcuts[modifierKey];
      if (modifierShortcut) {
        event.preventDefault();
        modifierShortcut(event);
      }
    };

    document.addEventListener('keydown', handleKeyPress);
    return () => {
      document.removeEventListener('keydown', handleKeyPress);
    };
  }, [shortcuts]);
}

/**
 * Hook for managing focus trap (for modals and dialogs)
 */
export function useFocusTrap(active: boolean, containerRef: React.RefObject<HTMLElement>) {
  useEffect(() => {
    if (!active || !containerRef.current) return;

    const container = containerRef.current;
    const focusableElements = container.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          lastElement.focus();
          e.preventDefault();
        }
      } else {
        if (document.activeElement === lastElement) {
          firstElement.focus();
          e.preventDefault();
        }
      }
    };

    // Focus first element
    if (firstElement) {
      firstElement.focus();
    }

    document.addEventListener('keydown', handleTabKey);
    return () => {
      document.removeEventListener('keydown', handleTabKey);
    };
  }, [active, containerRef]);
}

// Helper functions
const playNotificationSound = (type: 'success' | 'error' | 'warning' | 'info) => {
  try {
    const audio = new Audio(`/sounds/notification-${type}.mp3`);
    audio.volume = 0.5;
    audio.play().catch(() => {
      // Ignore audio play errors (user might have audio disabled)
    });
  } catch (error) {
    console.warn('Failed to play notification sound:', error);
  }
};

const showDesktopNotification = (notification: any) => {
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification(notification.title, {
      body: notification.message,
      icon: '/favicon.ico',
      tag: notification.id,
    });
  }
};
```

https://www.kimi.com/share/d2ump3u4bbjog46tgufg
