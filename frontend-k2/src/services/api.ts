import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios'
import { AuthTokens, ApiResponse, PaginatedResponse, AppError } from '@/types'
import toast from 'react-hot-toast'

class ApiClient {
  private client: AxiosInstance
  private authTokens: AuthTokens | null = null

  constructor(baseURL: string = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1') {
    this.client = axios.create({
      baseURL,
      timeout: 30000, // 30 seconds as per PRD v4 performance requirements
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.setupInterceptors()
  }

  private setupInterceptors(): void {
    // Request interceptor for auth
    this.client.interceptors.request.use(
      (config) => {
        if (this.authTokens?.access_token) {
          config.headers.Authorization = `Bearer ${this.authTokens.access_token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError<ApiResponse<any>>) => {
        if (error.response?.status === 401) {
          // Handle token refresh or redirect to login
          this.handleUnauthorized()
        } else if (error.response?.status === 429) {
          // Handle rate limiting
          toast.error('Too many requests. Please try again later.')
        } else if (error.response?.data?.error) {
          // Handle API errors
          const appError: AppError = {
            code: error.response.data.error || 'API_ERROR',
            message: error.response.data.message || 'An error occurred',
            timestamp: new Date().toISOString(),
            context: error.response.data,
          }
          toast.error(appError.message)
          throw appError
        } else if (error.code === 'ECONNABORTED') {
          // Handle timeout
          const timeoutError: AppError = {
            code: 'TIMEOUT_ERROR',
            message: 'Request timed out. Please check your connection.',
            timestamp: new Date().toISOString(),
          }
          toast.error(timeoutError.message)
          throw timeoutError
        } else if (!error.response) {
          // Handle network errors
          const networkError: AppError = {
            code: 'NETWORK_ERROR',
            message: 'Network error. Please check your connection.',
            timestamp: new Date().toISOString(),
          }
          toast.error(networkError.message)
          throw networkError
        }
        
        throw error
      }
    )
  }

  private handleUnauthorized(): void {
    // Clear stored tokens
    this.clearAuth()
    // Redirect to login or refresh token
    window.location.href = '/login'
  }

  setAuthTokens(tokens: AuthTokens): void {
    this.authTokens = tokens
  }

  clearAuth(): void {
    this.authTokens = null
  }

  // Generic request methods with proper typing
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<ApiResponse<T>>(url, config)
    return response.data.data
  }

  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<ApiResponse<T>>(url, data, config)
    return response.data.data
  }

  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<ApiResponse<T>>(url, data, config)
    return response.data.data
  }

  async patch<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.patch<ApiResponse<T>>(url, data, config)
    return response.data.data
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<ApiResponse<T>>(url, config)
    return response.data.data
  }

  // Auth endpoints
  async login(email: string, password: string): Promise<UserProfile> {
    return this.post<UserProfile>('/auth/login', { email, password })
  }

  async logout(): Promise<void> {
    await this.post('/auth/logout')
    this.clearAuth()
  }

  async refreshToken(refreshToken: string): Promise<AuthTokens> {
    const tokens = await this.post<AuthTokens>('/auth/refresh', { refresh_token: refreshToken })
    this.setAuthTokens(tokens)
    return tokens
  }

  async getProfile(): Promise<UserProfile> {
    return this.get<UserProfile>('/auth/profile')
  }

  // Conversation endpoints
  async getConversations(params?: {
    page?: number;
    limit?: number;
    status?: string[];
    channel?: string[];
    priority?: string[];
    search?: string;
  }) {
    return this.get<PaginatedResponse<Conversation>>('/conversations', { params })
  }

  async getConversation(id: string): Promise<Conversation> {
    return this.get<Conversation>(`/conversations/${id}`)
  }

  async createConversation(data: any): Promise<Conversation> {
    return this.post<Conversation>('/conversations', data)
  }

  async updateConversation(id: string, data: Partial<Conversation>): Promise<Conversation> {
    return this.patch<Conversation>(`/conversations/${id}`, data)
  }

  async deleteConversation(id: string): Promise<void> {
    await this.delete(`/conversations/${id}`)
  }

  // Message endpoints
  async getMessages(conversationId: string, params?: {
    page?: number;
    limit?: number;
    before?: string;
    after?: string;
  }) {
    return this.get<PaginatedResponse<Message>>(`/conversations/${conversationId}/messages`, { params })
  }

  async sendMessage(conversationId: string, content: string, contentType?: string): Promise<Message> {
    return this.post<Message>(`/conversations/${conversationId}/messages`, {
      content,
      content_type: contentType || 'text',
    })
  }

  async updateMessage(messageId: string, content: string): Promise<Message> {
    return this.patch<Message>(`/messages/${messageId}`, { content })
  }

  async deleteMessage(messageId: string): Promise<void> {
    await this.delete(`/messages/${messageId}`)
  }

  async markAsRead(conversationId: string, messageId: string): Promise<void> {
    await this.post(`/conversations/${conversationId}/messages/${messageId}/read`)
  }

  // User endpoints
  async getUsers(params?: {
    page?: number;
    limit?: number;
    role?: string;
    is_active?: boolean;
  }) {
    return this.get<PaginatedResponse<User>>('/users', { params })
  }

  async getUser(id: string): Promise<User> {
    return this.get<User>(`/users/${id}`)
  }

  async updateUser(id: string, data: Partial<User>): Promise<User> {
    return this.patch<User>(`/users/${id}`, data)
  }

  // Analytics endpoints
  async getConversationMetrics(params?: {
    date_from?: string;
    date_to?: string;
    organization_id?: string;
  }) {
    return this.get('/analytics/conversation-metrics', { params })
  }

  async getAIMetrics(params?: {
    date_from?: string;
    date_to?: string;
    model_type?: string;
  }) {
    return this.get('/analytics/ai-metrics', { params })
  }

  // File upload endpoints
  async uploadFile(file: File, onProgress?: (progress: number) => void): Promise<{ url: string; id: string }> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await this.client.post<ApiResponse<{ url: string; id: string }>>('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(progress)
        }
      },
    })

    return response.data.data
  }

  // Health check
  async healthCheck(): Promise<{ status: string; timestamp: string; version: string }> {
    return this.get('/health')
  }
}

// Create singleton instance
const apiClient = new ApiClient()

export default apiClient
