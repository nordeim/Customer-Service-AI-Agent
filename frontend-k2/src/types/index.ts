// Core type definitions aligned with Database Schema v4 and PRD v4 requirements

// User types
export interface User {
  id: string;
  organization_id: string;
  email: string;
  email_verified: boolean;
  username?: string;
  first_name?: string;
  last_name?: string;
  display_name?: string;
  avatar_url?: string;
  phone_number?: string;
  role: string;
  is_admin: boolean;
  is_agent: boolean;
  customer_tier?: string;
  preferred_language: string;
  preferred_channel?: ConversationChannel;
  is_active: boolean;
  is_online: boolean;
  last_seen_at?: string;
  created_at: string;
  updated_at: string;
}

// Conversation types
export type ConversationStatus = 
  | 'initialized' 
  | 'active' 
  | 'waiting_for_user' 
  | 'waiting_for_agent' 
  | 'processing' 
  | 'escalated' 
  | 'transferred' 
  | 'resolved' 
  | 'abandoned' 
  | 'archived';

export type ConversationChannel =
  | 'web_chat'
  | 'mobile_ios'
  | 'mobile_android'
  | 'email'
  | 'slack'
  | 'teams'
  | 'whatsapp'
  | 'telegram'
  | 'sms'
  | 'voice'
  | 'api'
  | 'widget'
  | 'salesforce';

export type PriorityLevel = 'low' | 'medium' | 'high' | 'urgent' | 'critical';

export interface Conversation {
  id: string;
  organization_id: string;
  user_id: string;
  conversation_number: number;
  title?: string;
  description?: string;
  channel: ConversationChannel;
  source?: string;
  source_url?: string;
  status: ConversationStatus;
  priority: PriorityLevel;
  is_urgent: boolean;
  assigned_agent_id?: string;
  assigned_team?: string;
  assigned_queue?: string;
  assigned_at?: string;
  started_at: string;
  first_message_at?: string;
  first_response_at?: string;
  last_message_at?: string;
  last_activity_at: string;
  ended_at?: string;
  message_count: number;
  user_message_count: number;
  agent_message_count: number;
  ai_message_count: number;
  first_response_time?: number;
  average_response_time?: number;
  max_response_time?: number;
  ai_handled: boolean;
  ai_confidence_avg?: number;
  ai_resolution_score?: number;
  sentiment_initial?: SentimentLabel;
  sentiment_current: SentimentLabel;
  sentiment_final?: SentimentLabel;
  emotion_initial?: EmotionLabel;
  emotion_current: EmotionLabel;
  emotion_final?: EmotionLabel;
  primary_intent?: string;
  intent_confidence?: number;
  resolved: boolean;
  resolved_at?: string;
  resolution_time_seconds?: number;
  escalated: boolean;
  escalation_reason?: EscalationReason;
  escalated_at?: string;
  satisfaction_score?: number;
  nps_score?: number;
  csat_score?: number;
  language: string;
  context: Record<string, any>;
  salesforce_case_id?: string;
  category?: string;
  subcategory?: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

// Message types
export type MessageSenderType = 'user' | 'ai_agent' | 'human_agent' | 'system' | 'bot' | 'integration';
export type MessageContentType = 'text' | 'html' | 'markdown' | 'code' | 'json' | 'image' | 'audio' | 'video' | 'file' | 'card' | 'carousel' | 'quick_reply' | 'form';
export type SentimentLabel = 'very_negative' | 'negative' | 'neutral' | 'positive' | 'very_positive';
export type EmotionLabel = 'angry' | 'frustrated' | 'confused' | 'neutral' | 'satisfied' | 'happy' | 'excited';
export type EscalationReason = 'user_requested' | 'sentiment_negative' | 'emotion_angry' | 'low_confidence' | 'multiple_attempts' | 'complex_issue' | 'vip_customer' | 'compliance_required' | 'technical_error' | 'timeout' | 'manual_review';

export interface Message {
  id: string;
  conversation_id: string;
  organization_id: string;
  message_number?: number;
  sender_type: MessageSenderType;
  sender_id?: string;
  sender_name?: string;
  sender_email?: string;
  sender_avatar_url?: string;
  content: string;
  content_type: MessageContentType;
  content_encrypted: boolean;
  content_preview?: string;
  content_length?: number;
  content_html?: string;
  content_markdown?: string;
  content_json?: Record<string, any>;
  original_language?: string;
  detected_language?: string;
  content_translated?: string;
  translated_to?: string;
  translation_confidence?: number;
  intent?: string;
  intent_confidence?: number;
  entities: Array<Record<string, any>>;
  keywords: string[];
  topics: string[];
  sentiment_score?: number;
  sentiment_label?: SentimentLabel;
  sentiment_confidence?: number;
  emotion_label?: EmotionLabel;
  emotion_intensity?: number;
  ai_processed: boolean;
  ai_model_used?: string;
  ai_model_version?: string;
  ai_provider?: string;
  ai_processing_time_ms?: number;
  ai_tokens_used?: number;
  ai_cost?: number;
  ai_confidence?: number;
  is_flagged: boolean;
  is_internal: boolean;
  is_automated: boolean;
  is_system_generated: boolean;
  is_private: boolean;
  is_edited: boolean;
  edited_at?: string;
  edit_count: number;
  in_reply_to?: string;
  thread_id?: string;
  has_attachments: boolean;
  attachments: Array<Record<string, any>>;
  quick_replies?: Array<Record<string, any>>;
  actions?: Array<Record<string, any>>;
  delivered_at?: string;
  seen_at?: string;
  failed_delivery: boolean;
  delivery_attempts: number;
  metadata: Record<string, any>;
  created_at: string;
  sent_at?: string;
}

// API Response types
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  error?: string;
  metadata?: {
    total?: number;
    page?: number;
    limit?: number;
    has_next?: boolean;
    has_prev?: boolean;
  };
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  metadata: {
    total: number;
    page: number;
    limit: number;
    has_next: boolean;
    has_prev: boolean;
    total_pages: number;
  };
}

// WebSocket types
export interface WebSocketMessage {
  type: 'message' | 'typing' | 'status' | 'error' | 'connection';
  conversation_id?: string;
  data?: any;
  timestamp: string;
  correlation_id?: string;
}

export interface TypingIndicatorData {
  conversation_id: string;
  user_id?: string;
  user_name?: string;
  is_typing: boolean;
  timestamp: string;
}

// Auth types
export interface AuthTokens {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in: number;
}

export interface UserProfile {
  user: User;
  tokens: AuthTokens;
  permissions: string[];
  organization: Organization;
}

// UI State types
export interface UIState {
  theme: 'light' | 'dark';
  language: string;
  rtl: boolean;
  sidebarOpen: boolean;
  notifications: Notification[];
  loading: boolean;
  error: string | null;
}

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message?: string;
  timestamp: string;
  read: boolean;
  persistent?: boolean;
}

// Chat-specific types
export interface ChatState {
  conversations: Conversation[];
  currentConversation?: Conversation;
  messages: Message[];
  isLoading: boolean;
  isTyping: boolean;
  typingUsers: TypingIndicatorData[];
  hasMoreMessages: boolean;
  isSending: boolean;
  error: string | null;
}

export interface SendMessageData {
  content: string;
  content_type?: MessageContentType;
  conversation_id: string;
  parent_id?: string;
  attachments?: File[];
  metadata?: Record<string, any>;
}

export interface ConversationCreateData {
  title?: string;
  description?: string;
  channel: ConversationChannel;
  priority?: PriorityLevel;
  context?: Record<string, any>;
  metadata?: Record<string, any>;
}

// Accessibility types
export interface A11yPreferences {
  reducedMotion: boolean;
  highContrast: boolean;
  largeText: boolean;
  screenReaderOptimized: boolean;
  keyboardNavigation: boolean;
  focusIndicators: boolean;
}

// Performance types
export interface PerformanceMetrics {
  pageLoadTime: number;
  timeToInteractive: number;
  firstInputDelay: number;
  cumulativeLayoutShift: number;
  largestContentfulPaint: number;
}

// Error types
export interface AppError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
  context?: Record<string, any>;
}

// Configuration types
export interface AppConfig {
  api: {
    baseUrl: string;
    timeout: number;
    retries: number;
  };
  websocket: {
    url: string;
    reconnectInterval: number;
    maxReconnectAttempts: number;
  };
  features: {
    analytics: boolean;
    notifications: boolean;
    offline: boolean;
    typingIndicators: boolean;
    messageDeliveryStatus: boolean;
    readReceipts: boolean;
  };
  ui: {
    theme: 'light' | 'dark' | 'auto';
    language: string;
    rtl: boolean;
    reducedMotion: boolean;
    fontSize: 'small' | 'medium' | 'large';
  };
  performance: {
    messageBatchSize: number;
    autoRefreshInterval: number;
    typingIndicatorDelay: number;
    debounceDelay: number;
  };
  accessibility: A11yPreferences;
}

// Real-time event types
export interface RealTimeEvent {
  id: string;
  type: string;
  payload: any;
  timestamp: string;
  correlation_id?: string;
}

// File upload types
export interface FileUpload {
  id: string;
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  error?: string;
  uploadedUrl?: string;
}

// Search and filtering types
export interface ConversationFilters {
  status?: ConversationStatus[];
  channel?: ConversationChannel[];
  priority?: PriorityLevel[];
  assigned_to?: string;
  has_unread?: boolean;
  date_from?: string;
  date_to?: string;
  search?: string;
  tags?: string[];
}

export interface SearchOptions {
  query: string;
  filters?: ConversationFilters;
  sort_by?: 'created_at' | 'updated_at' | 'priority' | 'status';
  sort_order?: 'asc' | 'desc';
  page?: number;
  limit?: number;
}

// Export all types
export type {
  User,
  Conversation,
  Message,
  Organization,
  AuthTokens,
  UserProfile,
  UIState,
  ChatState,
  SendMessageData,
  ConversationCreateData,
  A11yPreferences,
  PerformanceMetrics,
  AppError,
  AppConfig,
  RealTimeEvent,
  FileUpload,
  ConversationFilters,
  SearchOptions
};

// Re-export enums and constants
export {
  ConversationStatus,
  ConversationChannel,
  PriorityLevel,
  MessageSenderType,
  MessageContentType,
  SentimentLabel,
  EmotionLabel,
  EscalationReason
};
