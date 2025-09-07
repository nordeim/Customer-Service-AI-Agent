<think>
I need to continue with the same rigorous approach. Let me systematically complete:

1. WebSocket service
2. API service  
3. Auth service
4. Then move to components, hooks, and utilities

Each file needs to:
- Comply with PRD v4 accessibility requirements
- Use TypeScript strict mode
- Align with Database Schema v4
- Include proper error handling
- Follow security best practices
- Be evidence-based with clear implementation

Let me continue methodically with the services layer.
</think>

Continuing with Phase 8 implementation - Services layer:

## frontend/src/services/websocket/WebSocketService.ts
```typescript
import { EventEmitter } from 'events';
import { WebSocketMessage, TypingIndicator, ConversationStatus } from '@store/types';

interface WebSocketServiceConfig {
  url: string;
  protocols?: string[];
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  timeout?: number;
}

interface WebSocketEvents {
  connected: () => void;
  disconnected: (code: number, reason: string) => void;
  error: (error: Error) => void;
  message: (message: WebSocketMessage) => void;
  typing: (typing: TypingIndicator) => void;
  status: (status: ConversationStatus) => void;
  reconnecting: (attempt: number) => void;
  reconnected: () => void;
  pong: () => void;
}

export class WebSocketService extends EventEmitter {
  private ws: WebSocket | null = null;
  private config: Required<WebSocketServiceConfig>;
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private connectionId: string | null = null;
  private isIntentionallyClosed = false;
  private messageQueue: WebSocketMessage[] = [];
  private isConnecting = false;

  constructor(config: WebSocketServiceConfig) {
    super();
    this.config = {
      url: config.url,
      protocols: config.protocols || [],
      reconnectInterval: config.reconnectInterval || 1000,
      maxReconnectAttempts: config.maxReconnectAttempts || 5,
      heartbeatInterval: config.heartbeatInterval || 30000,
      timeout: config.timeout || 10000,
    };
  }

  /**
   * Connect to WebSocket server
   */
  public async connect(token: string): Promise<void> {
    if (this.isConnecting || this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.isIntentionallyClosed = false;
    this.isConnecting = true;

    try {
      const url = new URL(this.config.url);
      url.searchParams.set('token', token);
      
      this.ws = new WebSocket(url.toString(), this.config.protocols);
      this.setupEventListeners();
      
      await this.waitForConnection();
      this.isConnecting = false;
      this.reconnectAttempts = 0;
      this.startHeartbeat();
      this.flushMessageQueue();
      
      this.emit('connected');
    } catch (error) {
      this.isConnecting = false;
      this.handleConnectionError(error as Error);
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  public disconnect(): void {
    this.isIntentionallyClosed = true;
    this.clearReconnectTimer();
    this.clearHeartbeatTimer();
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    
    this.connectionId = null;
    this.emit('disconnected', 1000, 'Client disconnect');
  }

  /**
   * Send message through WebSocket
   */
  public send(message: WebSocketMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(message));
      } catch (error) {
        console.error('Failed to send WebSocket message:', error);
        this.messageQueue.push(message);
      }
    } else {
      // Queue message if not connected
      this.messageQueue.push(message);
    }
  }

  /**
   * Send typing indicator
   */
  public sendTypingIndicator(conversationId: string, isTyping: boolean): void {
    const message: WebSocketMessage = {
      type: 'typing',
      conversationId,
      data: { isTyping },
      timestamp: new Date().toISOString(),
      correlationId: this.generateCorrelationId(),
    };
    
    this.send(message);
  }

  /**
   * Send conversation status update
   */
  public sendStatusUpdate(conversationId: string, status: string): void {
    const message: WebSocketMessage = {
      type: 'status',
      conversationId,
      data: { status },
      timestamp: new Date().toISOString(),
      correlationId: this.generateCorrelationId(),
    };
    
    this.send(message);
  }

  /**
   * Send ping message
   */
  public sendPing(): void {
    const message: WebSocketMessage = {
      type: 'ping',
      conversationId: 'system',
      data: null,
      timestamp: new Date().toISOString(),
      correlationId: this.generateCorrelationId(),
    };
    
    this.send(message);
  }

  /**
   * Get connection status
   */
  public getConnectionStatus(): 'connected' | 'connecting' | 'disconnected' {
    if (this.isConnecting) return 'connecting';
    if (this.ws?.readyState === WebSocket.OPEN) return 'connected';
    return 'disconnected';
  }

  /**
   * Get connection ID
   */
  public getConnectionId(): string | null {
    return this.connectionId;
  }

  /**
   * Check if connected
   */
  public isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  // Private methods

  private setupEventListeners(): void {
    if (!this.ws) return;

    this.ws.onopen = this.handleOpen.bind(this);
    this.ws.onclose = this.handleClose.bind(this);
    this.ws.onerror = this.handleError.bind(this);
    this.ws.onmessage = this.handleMessage.bind(this);
  }

  private handleOpen(event: Event): void {
    console.log('WebSocket connected');
    this.isConnecting = false;
    
    // Extract connection ID from URL if available
    const url = new URL(this.config.url);
    this.connectionId = url.searchParams.get('connectionId') || this.generateConnectionId();
  }

  private handleClose(event: CloseEvent): void {
    console.log('WebSocket disconnected:', event.code, event.reason);
    this.clearHeartbeatTimer();
    this.connectionId = null;
    
    if (!this.isIntentionallyClosed && this.reconnectAttempts < this.config.maxReconnectAttempts) {
      this.scheduleReconnect();
    }
    
    this.emit('disconnected', event.code, event.reason);
  }

  private handleError(event: Event): void {
    const error = new Error('WebSocket error occurred');
    console.error('WebSocket error:', error);
    this.emit('error', error);
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      // Handle different message types
      switch (message.type) {
        case 'pong':
          this.handlePong();
          break;
        case 'typing':
          this.handleTypingIndicator(message as TypingIndicator);
          break;
        case 'status':
          this.handleStatusUpdate(message as ConversationStatus);
          break;
        case 'message':
          this.handleIncomingMessage(message);
          break;
        default:
          this.emit('message', message);
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  private handlePong(): void {
    this.emit('pong');
  }

  private handleTypingIndicator(typing: TypingIndicator): void {
    this.emit('typing', typing);
  }

  private handleStatusUpdate(status: ConversationStatus): void {
    this.emit('status', status);
  }

  private handleIncomingMessage(message: WebSocketMessage): void {
    this.emit('message', message);
  }

  private handleConnectionError(error: Error): void {
    console.error('WebSocket connection error:', error);
    this.emit('error', error);
    
    if (!this.isIntentionallyClosed && this.reconnectAttempts < this.config.maxReconnectAttempts) {
      this.scheduleReconnect();
    }
  }

  private waitForConnection(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.ws) {
        reject(new Error('WebSocket not initialized'));
        return;
      }

      const timeout = setTimeout(() => {
        reject(new Error('Connection timeout'));
      }, this.config.timeout);

      const handleOpen = () => {
        clearTimeout(timeout);
        this.ws!.removeEventListener('open', handleOpen);
        resolve();
      };

      const handleError = (event: Event) => {
        clearTimeout(timeout);
        this.ws!.removeEventListener('error', handleError);
        reject(new Error('Connection failed'));
      };

      this.ws.addEventListener('open', handleOpen);
      this.ws.addEventListener('error', handleError);
    });
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.attemptReconnect();
    }, this.config.reconnectInterval * Math.pow(2, this.reconnectAttempts));
    
    this.emit('reconnecting', this.reconnectAttempts + 1);
  }

  private attemptReconnect(): void {
    if (this.isIntentionallyClosed) return;
    
    console.log(`Attempting reconnection ${this.reconnectAttempts + 1}/${this.config.maxReconnectAttempts}`);
    
    // This would need to be implemented by the consumer to provide the token
    this.emit('reconnect', this.reconnectAttempts + 1);
  }

  private startHeartbeat(): void {
    this.clearHeartbeatTimer();
    
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected()) {
        this.sendPing();
      }
    }, this.config.heartbeatInterval);
  }

  private clearHeartbeatTimer(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.isConnected()) {
      const message = this.messageQueue.shift();
      if (message) {
        this.send(message);
      }
    }
  }

  private generateCorrelationId(): string {
    return `ws_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateConnectionId(): string {
    return `conn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// Singleton instance
let instance: WebSocketService | null = null;

export const websocketService = {
  getInstance: (config?: WebSocketServiceConfig): WebSocketService => {
    if (!instance) {
      if (!config) {
        throw new Error('WebSocketService requires configuration on first initialization');
      }
      instance = new WebSocketService(config);
    }
    return instance;
  },
  
  connect: async (token: string, url = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'): Promise<void> => {
    const service = websocketService.getInstance({
      url,
      reconnectInterval: 1000,
      maxReconnectAttempts: 5,
      heartbeatInterval: 30000,
    });
    return service.connect(token);
  },
  
  disconnect: (): void => {
    if (instance) {
      instance.disconnect();
    }
  },
  
  send: (message: WebSocketMessage): void => {
    if (instance) {
      instance.send(message);
    }
  },
  
  getConnectionStatus: (): 'connected' | 'connecting' | 'disconnected' => {
    return instance?.getConnectionStatus() || 'disconnected';
  },
  
  isConnected: (): boolean => {
    return instance?.isConnected() || false;
  },
};

// Export types
export type { WebSocketService, WebSocketServiceConfig, WebSocketEvents };
```

## frontend/src/services/api/apiService.ts
```typescript
import { APIResponse, APIError } from '@store/types';

interface RequestConfig extends RequestInit {
  timeout?: number;
  retries?: number;
  retryDelay?: number;
}

interface APIConfig {
  baseURL: string;
  timeout: number;
  retries: number;
  retryDelay: number;
  headers: Record<string, string>;
}

class APIService {
  private config: APIConfig;
  private abortControllers: Map<string, AbortController> = new Map();

  constructor(config: APIConfig) {
    this.config = config;
  }

  /**
   * Make a GET request
   */
  public async get<T>(url: string, config?: RequestConfig): Promise<APIResponse<T>> {
    return this.request<T>(url, { ...config, method: 'GET' });
  }

  /**
   * Make a POST request
   */
  public async post<T>(url: string, data?: unknown, config?: RequestConfig): Promise<APIResponse<T>> {
    return this.request<T>(url, { ...config, method: 'POST', body: JSON.stringify(data) });
  }

  /**
   * Make a PUT request
   */
  public async put<T>(url: string, data?: unknown, config?: RequestConfig): Promise<APIResponse<T>> {
    return this.request<T>(url, { ...config, method: 'PUT', body: JSON.stringify(data) });
  }

  /**
   * Make a PATCH request
   */
  public async patch<T>(url: string, data?: unknown, config?: RequestConfig): Promise<APIResponse<T>> {
    return this.request<T>(url, { ...config, method: 'PATCH', body: JSON.stringify(data) });
  }

  /**
   * Make a DELETE request
   */
  public async delete<T>(url: string, config?: RequestConfig): Promise<APIResponse<T>> {
    return this.request<T>(url, { ...config, method: 'DELETE' });
  }

  /**
   * Upload a file
   */
  public async upload<T>(url: string, file: File, onProgress?: (progress: number) => void, config?: RequestConfig): Promise<APIResponse<T>> {
    const formData = new FormData();
    formData.append('file', file);

    const requestConfig: RequestConfig = {
      ...config,
      body: formData,
      headers: {
        ...config?.headers,
        'Content-Type': undefined, // Let browser set content type for multipart
      },
    };

    if (onProgress) {
      requestConfig.onUploadProgress = (event) => {
        if (event.lengthComputable) {
          const progress = Math.round((event.loaded / event.total) * 100);
          onProgress(progress);
        }
      };
    }

    return this.request<T>(url, { ...requestConfig, method: 'POST' });
  }

  /**
   * Download a file
   */
  public async download(url: string, config?: RequestConfig): Promise<Blob> {
    const response = await this.fetchWithTimeout(url, { ...config, method: 'GET' });
    
    if (!response.ok) {
      throw new Error(`Download failed: ${response.statusText}`);
    }
    
    return response.blob();
  }

  /**
   * Cancel a specific request
   */
  public cancelRequest(requestId: string): void {
    const controller = this.abortControllers.get(requestId);
    if (controller) {
      controller.abort();
      this.abortControllers.delete(requestId);
    }
  }

  /**
   * Cancel all pending requests
   */
  public cancelAllRequests(): void {
    this.abortControllers.forEach((controller) => controller.abort());
    this.abortControllers.clear();
  }

  /**
   * Make a request with retry logic
   */
  private async request<T>(url: string, config: RequestConfig): Promise<APIResponse<T>> {
    const { timeout = this.config.timeout, retries = this.config.retries, retryDelay = this.config.retryDelay } = config;
    const requestId = this.generateRequestId();
    
    let lastError: Error | null = null;
    
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const response = await this.fetchWithRetry(url, config, requestId, attempt);
        return await this.handleResponse<T>(response);
      } catch (error) {
        lastError = error as Error;
        
        if (attempt < retries && this.shouldRetry(error as Error)) {
          await this.delay(retryDelay * Math.pow(2, attempt)); // Exponential backoff
          continue;
        }
        
        break;
      } finally {
        this.abortControllers.delete(requestId);
      }
    }
    
    return this.createErrorResponse<T>(lastError || new Error('Request failed'));
  }

  /**
   * Make a fetch request with timeout
   */
  private async fetchWithTimeout(url: string, config: RequestConfig, requestId: string): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.timeout || this.config.timeout);
    
    this.abortControllers.set(requestId, controller);
    
    try {
      const fullUrl = this.buildURL(url);
      const requestConfig: RequestInit = {
        ...config,
        signal: controller.signal,
        headers: {
          ...this.config.headers,
          ...config.headers,
        },
      };
      
      return await fetch(fullUrl, requestConfig);
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * Make a fetch request with retry logic
   */
  private async fetchWithRetry(url: string, config: RequestConfig, requestId: string, attempt: number): Promise<Response> {
    try {
      return await this.fetchWithTimeout(url, config, requestId);
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError' && attempt === 0) {
        throw new Error('Request timeout');
      }
      throw error;
    }
  }

  /**
   * Handle the response and parse data
   */
  private async handleResponse<T>(response: Response): Promise<APIResponse<T>> {
    const contentType = response.headers.get('content-type');
    const isJson = contentType?.includes('application/json');
    
    if (!response.ok) {
      const errorData = isJson ? await response.json() : await response.text();
      const error: APIError = {
        code: response.status.toString(),
        message: this.getErrorMessage(response.status, errorData),
        details: isJson ? errorData : { text: errorData },
        timestamp: new Date().toISOString(),
      };
      
      return {
        data: null as any,
        status: response.status,
        errors: [error],
      };
    }
    
    let data: T;
    
    if (isJson) {
      data = await response.json();
    } else if (contentType?.includes('text/')) {
      data = await response.text() as unknown as T;
    } else {
      data = await response.blob() as unknown as T;
    }
    
    return {
      data,
      status: response.status,
      metadata: this.extractMetadata(response),
    };
  }

  /**
   * Build full URL from path
   */
  private buildURL(url: string): string {
    if (url.startsWith('http')) {
      return url;
    }
    return `${this.config.baseURL.replace(/\/$/, '')}/${url.replace(/^\//, '')}`;
  }

  /**
   * Extract metadata from response headers
   */
  private extractMetadata(response: Response): Record<string, unknown> {
    const metadata: Record<string, unknown> = {};
    
    // Extract pagination metadata if available
    const totalCount = response.headers.get('X-Total-Count');
    if (totalCount) {
      metadata.totalCount = parseInt(totalCount, 10);
    }
    
    const page = response.headers.get('X-Page');
    if (page) {
      metadata.page = parseInt(page, 10);
    }
    
    const pageSize = response.headers.get('X-Page-Size');
    if (pageSize) {
      metadata.pageSize = parseInt(pageSize, 10);
    }
    
    const hasMore = response.headers.get('X-Has-More');
    if (hasMore) {
      metadata.hasMore = hasMore === 'true';
    }
    
    return metadata;
  }

  /**
   * Get user-friendly error message based on status code
   */
  private getErrorMessage(status: number, errorData: any): string {
    if (typeof errorData === 'object' && errorData?.message) {
      return errorData.message;
    }
    
    switch (status) {
      case 400:
        return 'Bad request. Please check your input.';
      case 401:
        return 'Unauthorized. Please log in again.';
      case 403:
        return 'Forbidden. You do not have permission to perform this action.';
      case 404:
        return 'Resource not found.';
      case 409:
        return 'Conflict. The resource already exists or has been modified.';
      case 422:
        return 'Validation error. Please check your input.';
      case 429:
        return 'Too many requests. Please try again later.';
      case 500:
        return 'Internal server error. Please try again later.';
      case 502:
        return 'Bad gateway. The server is temporarily unavailable.';
      case 503:
        return 'Service unavailable. Please try again later.';
      default:
        return 'An unexpected error occurred.';
    }
  }

  /**
   * Determine if request should be retried
   */
  private shouldRetry(error: Error): boolean {
    // Retry on network errors
    if (error.message.includes('network') || error.message.includes('fetch')) {
      return true;
    }
    
    // Retry on timeout
    if (error.message.includes('timeout')) {
      return true;
    }
    
    return false;
  }

  /**
   * Create error response
   */
  private createErrorResponse<T>(error: Error): APIResponse<T> {
    return {
      data: null as any,
      status: 0,
      errors: [{
        code: 'REQUEST_ERROR',
        message: error.message,
        details: { error: error.message, stack: error.stack },
        timestamp: new Date().toISOString(),
      }],
    };
  }

  /**
   * Delay execution for specified milliseconds
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Generate unique request ID
   */
  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// API service instance
const apiService = new APIService({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  timeout: 30000,
  retries: 3,
  retryDelay: 1000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Client-Version': import.meta.env.npm_package_version || '1.0.0',
  },
});

// Export singleton instance
export { apiService as default };
export { APIService };
export type { RequestConfig, APIConfig };
```

## frontend/src/services/auth/tokenService.ts
```typescript
import { jwtDecode, JwtPayload } from 'jwt-decode';

interface TokenPayload extends JwtPayload {
  userId?: string;
  organizationId?: string;
  role?: string;
  permissions?: string[];
}

interface TokenData {
  token: string;
  refreshToken: string;
  expiresAt: string;
}

class TokenService {
  private readonly TOKEN_KEY = 'auth_token';
  private readonly REFRESH_TOKEN_KEY = 'auth_refresh_token';
  private readonly EXPIRES_AT_KEY = 'auth_expires_at';
  private readonly REMEMBER_ME_KEY = 'auth_remember_me';

  /**
   * Store authentication tokens
   */
  public setTokens(data: TokenData, rememberMe = false): void {
    this.setToken(data.token, rememberMe);
    this.setRefreshToken(data.refreshToken, rememberMe);
    this.setExpiresAt(data.expiresAt, rememberMe);
  }

  /**
   * Get stored token
   */
  public getToken(): string | null {
    return this.getItem(this.TOKEN_KEY);
  }

  /**
   * Set token
   */
  public setToken(token: string, rememberMe = false): void {
    this.setItem(this.TOKEN_KEY, token, rememberMe);
  }

  /**
   * Get refresh token
   */
  public getRefreshToken(): string | null {
    return this.getItem(this.REFRESH_TOKEN_KEY);
  }

  /**
   * Set refresh token
   */
  public setRefreshToken(refreshToken: string, rememberMe = false): void {
    this.setItem(this.REFRESH_TOKEN_KEY, refreshToken, rememberMe);
  }

  /**
   * Get token expiration time
   */
  public getExpiresAt(): string | null {
    return this.getItem(this.EXPIRES_AT_KEY);
  }

  /**
   * Set token expiration time
   */
  public setExpiresAt(expiresAt: string, rememberMe = false): void {
    this.setItem(this.EXPIRES_AT_KEY, expiresAt, rememberMe);
  }

  /**
   * Clear all tokens
   */
  public clearTokens(): void {
    this.removeItem(this.TOKEN_KEY);
    this.removeItem(this.REFRESH_TOKEN_KEY);
    this.removeItem(this.EXPIRES_AT_KEY);
    this.removeItem(this.REMEMBER_ME_KEY);
  }

  /**
   * Check if token is expired
   */
  public isTokenExpired(token?: string): boolean {
    const tokenToCheck = token || this.getToken();
    if (!tokenToCheck) return true;

    try {
      const decoded = jwtDecode<TokenPayload>(tokenToCheck);
      const currentTime = Date.now() / 1000;
      
      // Check if token has expired
      if (decoded.exp && decoded.exp < currentTime) {
        return true;
      }
      
      // Check if token will expire soon (within 5 minutes)
      if (decoded.exp && decoded.exp < currentTime + 300) {
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Failed to decode token:', error);
      return true;
    }
  }

  /**
   * Check if token will expire soon
   */
  public willTokenExpireSoon(token?: string, thresholdMinutes = 5): boolean {
    const tokenToCheck = token || this.getToken();
    if (!tokenToCheck) return true;

    try {
      const decoded = jwtDecode<TokenPayload>(tokenToCheck);
      const currentTime = Date.now() / 1000;
      const threshold = thresholdMinutes * 60;
      
      return decoded.exp ? decoded.exp < currentTime + threshold : true;
    } catch (error) {
      console.error('Failed to decode token:', error);
      return true;
    }
  }

  /**
   * Get time until token expires
   */
  public getTimeUntilExpiry(token?: string): number {
    const tokenToCheck = token || this.getToken();
    if (!tokenToCheck) return 0;

    try {
      const decoded = jwtDecode<TokenPayload>(tokenToCheck);
      const currentTime = Date.now() / 1000;
      
      return decoded.exp ? Math.max(0, decoded.exp - currentTime) : 0;
    } catch (error) {
      console.error('Failed to decode token:', error);
      return 0;
    }
  }

  /**
   * Decode token payload
   */
  public decodeToken(token?: string): TokenPayload | null {
    const tokenToCheck = token || this.getToken();
    if (!tokenToCheck) return null;

    try {
      return jwtDecode<TokenPayload>(tokenToCheck);
    } catch (error) {
      console.error('Failed to decode token:', error);
      return null;
    }
  }

  /**
   * Get user ID from token
   */
  public getUserId(): string | null {
    const decoded = this.decodeToken();
    return decoded?.userId || null;
  }

  /**
   * Get organization ID from token
   */
  public getOrganizationId(): string | null {
    const decoded = this.decodeToken();
    return decoded?.organizationId || null;
  }

  /**
   * Get user role from token
   */
  public getUserRole(): string | null {
    const decoded = this.decodeToken();
    return decoded?.role || null;
  }

  /**
   * Check if user has specific permission
   */
  public hasPermission(permission: string): boolean {
    const decoded = this.decodeToken();
    return decoded?.permissions?.includes(permission) || false;
  }

  /**
   * Check if user has any of the specified permissions
   */
  public hasAnyPermission(permissions: string[]): boolean {
    const decoded = this.decodeToken();
    if (!decoded?.permissions) return false;
    
    return permissions.some(permission => decoded.permissions!.includes(permission));
  }

  /**
   * Check if user has all of the specified permissions
   */
  public hasAllPermissions(permissions: string[]): boolean {
    const decoded = this.decodeToken();
    if (!decoded?.permissions) return false;
    
    return permissions.every(permission => decoded.permissions!.includes(permission));
  }

  /**
   * Validate token format
   */
  public isValidTokenFormat(token: string): boolean {
    // JWT tokens have three parts separated by dots
    const parts = token.split('.');
    return parts.length === 3;
  }

  /**
   * Get token issuer
   */
  public getTokenIssuer(): string | null {
    const decoded = this.decodeToken();
    return decoded?.iss || null;
  }

  /**
   * Get token audience
   */
  public getTokenAudience(): string | string[] | null {
    const decoded = this.decodeToken();
    return decoded?.aud || null;
  }

  /**
   * Get token issued at time
   */
  public getTokenIssuedAt(): number | null {
    const decoded = this.decodeToken();
    return decoded?.iat || null;
  }

  /**
   * Get token not before time
   */
  public getTokenNotBefore(): number | null {
    const decoded = this.decodeToken();
    return decoded?.nbf || null;
  }

  /**
   * Set remember me preference
   */
  public setRememberMe(rememberMe: boolean): void {
    this.setItem(this.REMEMBER_ME_KEY, rememberMe.toString(), true);
  }

  /**
   * Get remember me preference
   */
  public getRememberMe(): boolean {
    const value = this.getItem(this.REMEMBER_ME_KEY);
    return value === 'true';
  }

  // Private methods

  private getItem(key: string): string | null {
    try {
      return localStorage.getItem(key);
    } catch (error) {
      console.warn(`Failed to get item from localStorage: ${key}`, error);
      return null;
    }
  }

  private setItem(key: string, value: string, rememberMe = false): void {
    try {
      if (rememberMe) {
        localStorage.setItem(key, value);
      } else {
        sessionStorage.setItem(key, value);
      }
    } catch (error) {
      console.warn(`Failed to set item in storage: ${key}`, error);
    }
  }

  private removeItem(key: string): void {
    try {
      localStorage.removeItem(key);
      sessionStorage.removeItem(key);
    } catch (error) {
      console.warn(`Failed to remove item from storage: ${key}`, error);
    }
  }
}

// Export singleton instance
export const tokenService = new TokenService();
export default tokenService;
```

## frontend/src/services/api/auth.ts
```typescript
import { api } from '../index';
import { APIResponse } from '../types';

// Authentication API endpoints
export const authAPI = api.injectEndpoints({
  endpoints: (builder) => ({
    // Login
    login: builder.mutation<APIResponse<{
      user: any;
      organization: any;
      token: string;
      refreshToken: string;
      expiresAt: string;
      mfaRequired?: boolean;
    }>, {
      email: string;
      password: string;
      rememberMe?: boolean;
      deviceInfo?: {
        userAgent: string;
        ipAddress?: string;
      };
    }>>({
      query: (body) => ({
        url: '/auth/login',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['User'],
    }),
    
    // Logout
    logout: builder.mutation<APIResponse<void>, void>({
      query: () => ({
        url: '/auth/logout',
        method: 'POST',
      }),
    }),
    
    // Refresh token
    refreshToken: builder.mutation<APIResponse<{
      token: string;
      refreshToken: string;
      expiresAt: string;
    }>, {
      refreshToken: string;
    }>>({
      query: (body) => ({
        url: '/auth/refresh',
        method: 'POST',
        body,
      }),
    }),
    
    // Verify MFA
    verifyMFA: builder.mutation<APIResponse<void>, {
      code: string;
      deviceId?: string;
    }>>({
      query: (body) => ({
        url: '/auth/mfa/verify',
        method: 'POST',
        body,
      }),
    }),
    
    // Get current user
    getCurrentUser: builder.query<APIResponse<any>, void>({
      query: () => ({
        url: '/auth/me',
        method: 'GET',
      }),
      providesTags: ['User'],
    }),
    
    // Update user profile
    updateProfile: builder.mutation<APIResponse<any>, {
      firstName?: string;
      lastName?: string;
      displayName?: string;
      avatarUrl?: string;
      phoneNumber?: string;
      preferences?: Record<string, any>;
    }>>({
      query: (body) => ({
        url: '/auth/profile',
        method: 'PUT',
        body,
      }),
      invalidatesTags: ['User'],
    }),
    
    // Change password
    changePassword: builder.mutation<APIResponse<void>, {
      currentPassword: string;
      newPassword: string;
    }>>({
      query: (body) => ({
        url: '/auth/password',
        method: 'PUT',
        body,
      }),
    }),
    
    // Request password reset
    requestPasswordReset: builder.mutation<APIResponse<void>, {
      email: string;
    }>>({
      query: (body) => ({
        url: '/auth/password/reset',
        method: 'POST',
        body,
      }),
    }),
    
    // Reset password
    resetPassword: builder.mutation<APIResponse<void>, {
      token: string;
      newPassword: string;
    }>>({
      query: (body) => ({
        url: '/auth/password/reset/confirm',
        method: 'POST',
        body,
      }),
    }),
    
    // Enable MFA
    enableMFA: builder.mutation<APIResponse<{
      secret: string;
      qrCode: string;
      backupCodes: string[];
    }>, void>({
      query: () => ({
        url: '/auth/mfa/enable',
        method: 'POST',
      }),
    }),
    
    // Disable MFA
    disableMFA: builder.mutation<APIResponse<void>, {
      password: string;
    }>>({
      query: (body) => ({
        url: '/auth/mfa/disable',
        method: 'POST',
        body,
      }),
    }),
    
    // Get MFA backup codes
    getMFABackupCodes: builder.query<APIResponse<{
      backupCodes: string[];
    }>, void>({
      query: () => ({
        url: '/auth/mfa/backup-codes',
        method: 'GET',
      }),
    }),
    
    // Regenerate MFA backup codes
    regenerateMFABackupCodes: builder.mutation<APIResponse<{
      backupCodes: string[];
    }>, void>({
      query: () => ({
        url: '/auth/mfa/backup-codes/regenerate',
        method: 'POST',
      }),
    }),
    
    // Get user sessions
    getUserSessions: builder.query<APIResponse<Array<{
      id: string;
      deviceInfo: any;
      ipAddress: string;
      lastActiveAt: string;
      isCurrentSession: boolean;
    }>>>, void>({
      query: () => ({
        url: '/auth/sessions',
        method: 'GET',
      }),
    }),
    
    // Revoke session
    revokeSession: builder.mutation<APIResponse<void>, {
      sessionId: string;
    }>>({
      query: ({ sessionId }) => ({
        url: `/auth/sessions/${sessionId}`,
        method: 'DELETE',
      }),
    }),
    
    // Revoke all sessions except current
    revokeAllOtherSessions: builder.mutation<APIResponse<void>, void>({
      query: () => ({
        url: '/auth/sessions/revoke-all',
        method: 'POST',
      }),
    }),
    
    // Verify email
    verifyEmail: builder.mutation<APIResponse<void>, {
      token: string;
    }>>({
      query: (body) => ({
        url: '/auth/email/verify',
        method: 'POST',
        body,
      }),
    }),
    
    // Resend verification email
    resendVerificationEmail: builder.mutation<APIResponse<void>, void>({
      query: () => ({
        url: '/auth/email/resend',
        method: 'POST',
      }),
    }),
    
    // Get organization info
    getOrganization: builder.query<APIResponse<any>, void>({
      query: () => ({
        url: '/auth/organization',
        method: 'GET',
      }),
      providesTags: ['Organization'],
    }),
    
    // Update organization settings
    updateOrganizationSettings: builder.mutation<APIResponse<any>, {
      settings: Record<string, any>;
    }>>({
      query: (body) => ({
        url: '/auth/organization/settings',
        method: 'PUT',
        body,
      }),
      invalidatesTags: ['Organization'],
    }),
    
    // Get API key
    getApiKey: builder.query<APIResponse<{
      apiKey: string;
      maskedKey: string;
      createdAt: string;
      lastUsedAt?: string;
    }>, void>({
      query: () => ({
        url: '/auth/api-key',
        method: 'GET',
      }),
    }),
    
    // Regenerate API key
    regenerateApiKey: builder.mutation<APIResponse<{
      apiKey: string;
      maskedKey: string;
    }>, void>({
      query: () => ({
        url: '/auth/api-key/regenerate',
        method: 'POST',
      }),
    }),
    
    // Revoke API key
    revokeApiKey: builder.mutation<APIResponse<void>, void>({
      query: () => ({
        url: '/auth/api-key',
        method: 'DELETE',
      }),
    }),
    
    // Get audit log
    getAuditLog: builder.query<APIResponse<Array<{
      id: string;
      action: string;
      timestamp: string;
      ipAddress: string;
      userAgent: string;
      success: boolean;
    }>>>, {
      page?: number;
      pageSize?: number;
      dateFrom?: string;
      dateTo?: string;
    }>>({
      query: (params) => ({
        url: '/auth/audit-log',
        method: 'GET',
        params,
      }),
    }),
  }),
});

// Export hooks
export const {
  useLoginMutation,
  useLogoutMutation,
  useRefreshTokenMutation,
  useVerifyMFAMutation,
  useGetCurrentUserQuery,
  useUpdateProfileMutation,
  useChangePasswordMutation,
  useRequestPasswordResetMutation,
  useResetPasswordMutation,
  useEnableMFAMutation,
  useDisableMFAMutation,
  useGetMFABackupCodesQuery,
  useRegenerateMFABackupCodesMutation,
  useGetUserSessionsQuery,
  useRevokeSessionMutation,
  useRevokeAllOtherSessionsMutation,
  useVerifyEmailMutation,
  useResendVerificationEmailMutation,
  useGetOrganizationQuery,
  useUpdateOrganizationSettingsMutation,
  useGetApiKeyQuery,
  useRegenerateApiKeyMutation,
  useRevokeApiKeyMutation,
  useGetAuditLogQuery,
} = authAPI;

export { authAPI };
```

Now let me create the core components structure:

## frontend/src/components/Chat/ChatWindow.tsx
```typescript
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useDispatch } from 'react-redux';
import { useParams } from 'react-router-dom';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { TypingIndicator } from './TypingIndicator';
import { ChatHeader } from './ChatHeader';
import { QuickActions } from './QuickActions';
import { useConversation } from '@hooks/useConversation';
import { useWebSocket } from '@hooks/useWebSocket';
import { useAppSelector } from '@store/hooks';
import { AccessibilityAnnouncer } from '@components/Accessibility/AccessibilityAnnouncer';
import { LoadingSpinner } from '@components/UI/LoadingSpinner';
import { ErrorBoundary } from '@components/Error/ErrorBoundary';
import { ChatContainer } from './ChatContainer';
import { useTranslation } from 'react-i18next';
import { conversationSlice } from '@store/slices/conversationSlice';
import { websocketService } from '@services/websocket/websocketService';
import type { RootState } from '@store/types';

interface ChatWindowProps {
  className?: string;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({ className = '' }) => {
  const { t } = useTranslation();
  const dispatch = useDispatch();
  const { conversationId } = useParams<{ conversationId: string }>();
  const { currentConversation, sendMessage } = useConversation(conversationId);
  const { isConnected } = useWebSocket();
  const chatSettings = useAppSelector((state: RootState) => state.ui.chat);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typingUsers, setTypingUsers] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Load conversation data
  useEffect(() => {
    const loadConversation = async () => {
      if (!conversationId) return;

      setIsLoading(true);
      setError(null);

      try {
        // Fetch conversation and messages
        await Promise.all([
          dispatch(conversationSlice.actions.fetchConversation(conversationId)),
          dispatch(conversationSlice.actions.fetchMessages({ conversationId })),
        ]);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load conversation');
      } finally {
        setIsLoading(false);
      }
    };

    loadConversation();
  }, [dispatch, conversationId]);

  // Handle typing indicators
  useEffect(() => {
    if (!currentConversation) return;

    const handleTypingUpdate = (event: CustomEvent) => {
      const { conversationId: typingConversationId, userId, userName, isTyping } = event.detail;
      
      if (typingConversationId === currentConversation.id) {
        setTypingUsers(prev => {
          if (isTyping) {
            return [...prev.filter(id => id !== userId), userId];
          } else {
            return prev.filter(id => id !== userId);
          }
        });
      }
    };

    window.addEventListener('typing-indicator', handleTypingUpdate as EventListener);
    return () => window.removeEventListener('typing-indicator', handleTypingUpdate as EventListener);
  }, [currentConversation]);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    if (chatSettings.autoScroll && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatSettings.autoScroll]);

  // Handle message submission
  const handleSendMessage = useCallback(
    async (content: string, contentType = 'text') => {
      if (!currentConversation || !isConnected) return;

      try {
        await sendMessage(content, contentType);
        scrollToBottom();
        
        // Announce to screen readers
        const announcement = t('chat.messageSent', { content: content.substring(0, 50) });
        dispatch({
          type: 'accessibility/announce',
          payload: announcement,
        });
      } catch (error) {
        console.error('Failed to send message:', error);
        setError(error instanceof Error ? error.message : 'Failed to send message');
      }
    },
    [currentConversation, isConnected, sendMessage, scrollToBottom, t, dispatch]
  );

  // Handle quick action selection
  const handleQuickAction = useCallback(
    async (action: string, data?: Record<string, unknown>) => {
      if (!currentConversation) return;

      try {
        switch (action) {
          case 'escalate':
            await dispatch(
              conversationSlice.actions.escalateConversation({
                conversationId: currentConversation.id,
                reason: data?.reason as string || 'User requested escalation',
              })
            );
            break;
          case 'resolve':
            await dispatch(
              conversationSlice.actions.updateConversationStatus({
                conversationId: currentConversation.id,
                status: 'resolved',
              })
            );
            break;
          case 'transfer':
            // Handle transfer logic
            break;
          default:
            console.warn('Unknown quick action:', action);
        }
      } catch (error) {
        console.error('Failed to execute quick action:', error);
      }
    },
    [currentConversation, dispatch]
  );

  // Handle file upload
  const handleFileUpload = useCallback(
    async (file: File) => {
      if (!currentConversation) return;

      try {
        // Implement file upload logic
        const formData = new FormData();
        formData.append('file', file);
        
        // Upload file and get response
        // await dispatch(uploadAttachment({ conversationId: currentConversation.id, file }));
        
        // Send message with attachment
        await handleSendMessage(`Uploaded file: ${file.name}`, 'file');
      } catch (error) {
        console.error('Failed to upload file:', error);
        setError(error instanceof Error ? error.message : 'Failed to upload file');
      }
    },
    [currentConversation, handleSendMessage]
  );

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        // Clear current conversation
        dispatch(conversationSlice.actions.setCurrentConversation(null));
      }
      
      if (event.ctrlKey && event.key === 'r') {
        event.preventDefault();
        // Refresh conversation
        if (currentConversation) {
          dispatch(conversationSlice.actions.fetchMessages({ conversationId: currentConversation.id }));
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [dispatch, currentConversation]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full" role="status">
        <LoadingSpinner size="large" />
        <span className="sr-only">{t('chat.loading')}</span>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8" role="alert">
        <div className="text-error text-center">
          <h2 className="text-xl font-semibold mb-2">{t('chat.error.title')}</h2>
          <p className="mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="btn btn-primary"
            aria-label={t('chat.error.retry')}
          >
            {t('chat.error.retry')}
          </button>
        </div>
      </div>
    );
  }

  // No conversation selected
  if (!currentConversation && !conversationId) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <div className="text-muted-foreground">
          <h2 className="text-xl font-semibold mb-2">{t('chat.noConversation.title')}</h2>
          <p className="mb-4">{t('chat.noConversation.message')}</p>
          <button
            onClick={() => {
              // Create new conversation
              dispatch(conversationSlice.actions.createConversation({}));
            }}
            className="btn btn-primary"
            aria-label={t('chat.newConversation')}
          >
            {t('chat.newConversation')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <ChatContainer
        ref={chatContainerRef}
        className={className}
        aria-label={t('chat.containerLabel')}
      >
        {/* Chat Header */}
        <ChatHeader
          conversation={currentConversation}
          isConnected={isConnected}
          onQuickAction={handleQuickAction}
        />

        {/* Messages Area */}
        <div className="flex-1 overflow-hidden relative">
          <MessageList
            messages={currentConversation?.messages || []}
            currentUserId={useAppSelector((state: RootState) => state.auth.user?.id)}
            showTimestamps={chatSettings.showTimestamps}
            showAvatars={chatSettings.showAvatars}
            compactMode={chatSettings.compactMode}
            onMessageAction={(messageId, action) => {
              // Handle message actions (edit, delete, etc.)
            }}
          />
          
          {/* Typing Indicator */}
          {typingUsers.length > 0 && (
            <TypingIndicator
              users={typingUsers}
              className="absolute bottom-4 left-4"
            />
          )}
          
          {/* Messages End Marker */}
          <div ref={messagesEndRef} className="h-1" aria-hidden="true" />
        </div>

        {/* Quick Actions */}
        <QuickActions
          onAction={handleQuickAction}
          className="border-t border-border"
        />

        {/* Message Input */}
        <MessageInput
          onSendMessage={handleSendMessage}
          onFileUpload={handleFileUpload}
          disabled={!isConnected}
          enterToSend={chatSettings.enterToSend}
          placeholder={t('chat.inputPlaceholder')}
          aria-label={t('chat.inputLabel')}
        />

        {/* Connection Status */}
        {!isConnected && (
          <div className="absolute top-0 left-0 right-0 bg-warning/10 text-warning p-2 text-center text-sm">
            {t('chat.disconnected')}
          </div>
        )}

        {/* Accessibility Announcer */}
        <AccessibilityAnnouncer />
      </ChatContainer>
    </ErrorBoundary>
  );
};

export default ChatWindow;
```

## frontend/src/components/Chat/ChatContainer.tsx
```typescript
import React, { forwardRef } from 'react';
import { cn } from '@utils/cn';

interface ChatContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  role?: string;
  'aria-label'?: string;
}

export const ChatContainer = forwardRef<HTMLDivElement, ChatContainerProps>(
  ({ children, className, role = 'region', 'aria-label': ariaLabel, ...props }, ref) => {
    return (
      <div
        ref={ref}
        role={role}
        aria-label={ariaLabel || 'Chat conversation'}
        className={cn(
          'flex flex-col h-full bg-background',
          'border border-border rounded-lg',
          'shadow-sm overflow-hidden',
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

ChatContainer.displayName = 'ChatContainer';
```

## frontend/src/components/Chat/MessageList.tsx
```typescript
import React, { useEffect, useRef } from 'react';
import { MessageItem } from './MessageItem';
import { DateSeparator } from './DateSeparator';
import { useAppSelector } from '@store/hooks';
import { groupMessagesByDate } from '@utils/messageUtils';
import { useTranslation } from 'react-i18next';
import type { Message } from '@store/types';

interface MessageListProps {
  messages: Message[];
  currentUserId?: string;
  showTimestamps?: boolean;
  showAvatars?: boolean;
  compactMode?: boolean;
  onMessageAction?: (messageId: string, action: string) => void;
  className?: string;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  currentUserId,
  showTimestamps = true,
  showAvatars = true,
  compactMode = false,
  onMessageAction,
  className = '',
}) => {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement>(null);
  const { reducedMotion } = useAppSelector((state) => state.ui.accessibility);

  // Group messages by date
  const groupedMessages = groupMessagesByDate(messages);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (containerRef.current) {
      const container = containerRef.current;
      const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100;
      
      if (isNearBottom) {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: reducedMotion ? 'auto' : 'smooth',
        });
      }
    }
  }, [messages, reducedMotion]);

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
        event.preventDefault();
        
        const focusableElements = containerRef.current?.querySelectorAll<HTMLElement>('[tabindex="0"]');
        if (!focusableElements || focusableElements.length === 0) return;
        
        const currentIndex = Array.from(focusableElements).findIndex(el => el === document.activeElement);
        let nextIndex = currentIndex;
        
        if (event.key === 'ArrowUp') {
          nextIndex = currentIndex > 0 ? currentIndex - 1 : focusableElements.length - 1;
        } else {
          nextIndex = currentIndex < focusableElements.length - 1 ? currentIndex + 1 : 0;
        }
        
        focusableElements[nextIndex]?.focus();
      }
    };

    const container = containerRef.current;
    if (container) {
      container.addEventListener('keydown', handleKeyDown);
      return () => container.removeEventListener('keydown', handleKeyDown);
    }
  }, []);

  if (messages.length === 0) {
    return (
      <div 
        className="flex items-center justify-center h-full text-muted-foreground"
        role="status"
        aria-live="polite"
      >
        <div className="text-center">
          <div className="text-4xl mb-4">💬</div>
          <p className="text-lg">{t('chat.noMessages.title')}</p>
          <p className="text-sm mt-2">{t('chat.noMessages.description')}</p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`flex-1 overflow-y-auto p-4 space-y-4 ${className}`}
      role="log"
      aria-label={t('chat.messageListLabel')}
      aria-live="polite"
      tabIndex={0}
    >
      {Object.entries(groupedMessages).map(([date, dateMessages]) => (
        <div key={date} className="space-y-4">
          <DateSeparator date={date} />
          
          {dateMessages.map((message, index) => {
            const isCurrentUser = message.senderId === currentUserId;
            const showAvatar = showAvatars && !isCurrentUser;
            const previousMessage = index > 0 ? dateMessages[index - 1] : null;
            const isConsecutive = previousMessage?.senderId === message.senderId;
            const timeDiff = previousMessage 
              ? new Date(message.createdAt).getTime() - new Date(previousMessage.createdAt).getTime()
              : Infinity;
            const showTimestamp = showTimestamps && timeDiff > 60000; // 1 minute

            return (
              <MessageItem
                key={message.id}
                message={message}
                isCurrentUser={isCurrentUser}
                showAvatar={showAvatar}
                showTimestamp={showTimestamp}
                isConsecutive={isConsecutive}
                compactMode={compactMode}
                onAction={onMessageAction}
                tabIndex={0}
              />
            );
          })}
        </div>
      ))}
    </div>
  );
};

export default MessageList;
```

## frontend/src/components/Chat/MessageItem.tsx
```typescript
import React, { useState, useRef, useEffect } from 'react';
import { formatMessageTime, getMessageTypeIcon } from '@utils/messageUtils';
import { Avatar } from '@components/UI/Avatar';
import { DropdownMenu } from '@components/UI/DropdownMenu';
import { Button } from '@components/UI/Button';
import { cn } from '@utils/cn';
import { useTranslation } from 'react-i18next';
import { useAppSelector } from '@store/hooks';
import type { Message } from '@store/types';

interface MessageItemProps {
  message: Message;
  isCurrentUser: boolean;
  showAvatar?: boolean;
  showTimestamp?: boolean;
  isConsecutive?: boolean;
  compactMode?: boolean;
  onAction?: (messageId: string, action: string) => void;
  tabIndex?: number;
}

export const MessageItem: React.FC<MessageItemProps> = ({
  message,
  isCurrentUser,
  showAvatar = false,
  showTimestamp = false,
  isConsecutive = false,
  compactMode = false,
  onAction,
  tabIndex = 0,
}) => {
  const { t } = useTranslation();
  const { reducedMotion } = useAppSelector((state) => state.ui.accessibility);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const [showMenu, setShowMenu] = useState(false);
  const messageRef = useRef<HTMLDivElement>(null);

  // Handle message actions
  const handleAction = (action: string) => {
    if (onAction) {
      onAction(message.id, action);
    }
    setShowMenu(false);
  };

  // Handle edit submission
  const handleEditSubmit = () => {
    if (editContent.trim() && editContent !== message.content) {
      handleAction('edit');
    }
    setIsEditing(false);
  };

  // Handle edit cancellation
  const handleEditCancel = () => {
    setEditContent(message.content);
    setIsEditing(false);
  };

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (isEditing) {
        if (event.key === 'Enter' && !event.shiftKey) {
          event.preventDefault();
          handleEditSubmit();
        } else if (event.key === 'Escape') {
          event.preventDefault();
          handleEditCancel();
        }
      }
    };

    if (isEditing) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isEditing, editContent, message.content]);

  // Focus management for editing
  useEffect(() => {
    if (isEditing && messageRef.current) {
      const textarea = messageRef.current.querySelector('textarea');
      if (textarea) {
        textarea.focus();
        textarea.setSelectionRange(textarea.value.length, textarea.value.length);
      }
    }
  }, [isEditing]);

  const messageActions = [
    {
      label: t('chat.message.edit'),
      action: 'edit',
      icon: '✏️',
      visible: isCurrentUser && !message.isSystemGenerated,
    },
    {
      label: t('chat.message.copy'),
      action: 'copy',
      icon: '📋',
      visible: true,
    },
    {
      label: t('chat.message.delete'),
      action: 'delete',
      icon: '🗑️',
      visible: isCurrentUser && !message.isSystemGenerated,
    },
    {
      label: t('chat.message.report'),
      action: 'report',
      icon: '🚩',
      visible: !isCurrentUser,
    },
  ].filter(action => action.visible);

  const messageClassName = cn(
    'group relative flex items-start gap-3 p-3 rounded-lg transition-all',
    'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2',
    {
      'bg-primary/5': isCurrentUser,
      'bg-muted/50': !isCurrentUser,
      'ml-auto max-w-[70%]': isCurrentUser,
      'mr-auto max-w-[70%]': !isCurrentUser,
      'mb-1': isConsecutive && compactMode,
      'mb-4': !isConsecutive && !compactMode,
    }
  );

  const contentClassName = cn(
    'flex-1 space-y-1',
    {
      'text-right': isCurrentUser,
      'text-left': !isCurrentUser,
    }
  );

  return (
    <div
      ref={messageRef}
      className={messageClassName}
      tabIndex={tabIndex}
      role="article"
      aria-label={t('chat.messageLabel', { 
        sender: message.senderName || t('chat.unknownSender'),
        time: formatMessageTime(message.createdAt)
      })}
      onKeyDown={(e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
          setShowMenu(true);
        }
      }}
    >
      {/* Avatar */}
      {showAvatar && !isConsecutive && (
        <Avatar
          src={message.senderAvatarUrl}
          alt={message.senderName || t('chat.unknownSender')}
          size="sm"
          className="mt-1"
        />
      )}

      {/* Message content */}
      <div className={contentClassName}>
        {/* Sender name and timestamp */}
        {(showTimestamp || !isConsecutive) && (
          <div className={cn(
            'flex items-center gap-2 text-xs text-muted-foreground',
            {
              'justify-end': isCurrentUser,
              'justify-start': !isCurrentUser,
            }
          )}>
            {!isCurrentUser && !isConsecutive && (
              <span className="font-medium">{message.senderName}</span>
            )}
            {showTimestamp && (
              <time dateTime={message.createdAt} className="tabular-nums">
                {formatMessageTime(message.createdAt)}
              </time>
            )}
            {message.contentType !== 'text' && (
              <span className="flex items-center gap-1">
                {getMessageTypeIcon(message.contentType)}
                <span className="sr-only">{message.contentType}</span>
              </span>
            )}
          </div>
        )}

        {/* Message content */}
        <div className="relative">
          {isEditing ? (
            <div className="space-y-2">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full p-2 border rounded-md resize-none focus:ring-2 focus:ring-primary"
                rows={3}
                aria-label={t('chat.editMessage')}
              />
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={handleEditSubmit}
                  aria-label={t('common.save')}
                >
                  {t('common.save')}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleEditCancel}
                  aria-label={t('common.cancel')}
                >
                  {t('common.cancel')}
                </Button>
              </div>
            </div>
          ) : (
            <div className="relative group">
              <div
                className={cn(
                  'prose prose-sm max-w-none',
                  'text-foreground',
                  {
                    'whitespace-pre-wrap': message.contentType === 'text',
                    'font-mono text-xs': message.contentType === 'code',
                  }
                )}
                dangerouslySetInnerHTML={{
                  __html: sanitizeMessageContent(message.content),
                }}
              />
              
              {/* Action menu */}
              <DropdownMenu
                open={showMenu}
                onOpenChange={setShowMenu}
                trigger={
                  <Button
                    variant="ghost"
                    size="sm"
                    className={cn(
                      'absolute top-0 opacity-0 group-hover:opacity-100 transition-opacity',
                      {
                        'right-0': isCurrentUser,
                        'left-0': !isCurrentUser,
                      }
                    )}
                    aria-label={t('chat.message.actions')}
                  >
                    ⋯
                  </Button>
                }
              >
                {messageActions.map((action) => (
                  <DropdownMenu.Item
                    key={action.action}
                    onClick={() => handleAction(action.action)}
                    className="flex items-center gap-2"
                  >
                    <span>{action.icon}</span>
                    <span>{action.label}</span>
                  </DropdownMenu.Item>
                ))}
              </DropdownMenu>
            </div>
          )}
        </div>

        {/* Message metadata */}
        {message.isEdited && (
          <div className={cn(
            'text-xs text-muted-foreground',
            {
              'text-right': isCurrentUser,
              'text-left': !isCurrentUser,
            }
          )}>
            {t('chat.message.edited')}
          </div>
        )}

        {/* Sentiment indicator */}
        {message.sentimentLabel && (
          <div className={cn(
            'flex items-center gap-1 text-xs',
            {
              'justify-end': isCurrentUser,
              'justify-start': !isCurrentUser,
            }
          )}>
            <span className="sr-only">{t('chat.sentiment')}</span>
            <span role="img" aria-label={message.sentimentLabel}>
              {getSentimentEmoji(message.sentimentLabel)}
            </span>
          </div>
        )}
      </div>

      {/* Status indicators */}
      <div className={cn(
        'flex items-center gap-1 mt-1',
        {
          'justify-end': isCurrentUser,
          'justify-start': !isCurrentUser,
        }
      )}>
        {message.isEdited && (
          <span className="text-xs text-muted-foreground" aria-label={t('chat.message.edited')}>
            (edited)
          </span>
        )}
        {message.aiProcessed && (
          <span className="text-xs text-primary" aria-label={t('chat.message.aiProcessed')}>
            🤖
          </span>
        )}
        {message.isFlagged && (
          <span className="text-xs text-warning" aria-label={t('chat.message.flagged')}>
            ⚠️
          </span>
        )}
      </div>
    </div>
  );
};

// Helper functions

const sanitizeMessageContent = (content: string): string => {
  // Basic XSS protection
  return content
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;');
};

const getSentimentEmoji = (sentiment: string): string => {
  const emojiMap: Record<string, string> = {
    'very_positive': '😊',
    'positive': '🙂',
    'neutral': '😐',
    'negative': '😕',
    'very_negative': '😞',
  };
  return emojiMap[sentiment] || '😐';
};

export default MessageItem;
```

https://www.kimi.com/share/d2uo21t7vds29ndm1r4g
