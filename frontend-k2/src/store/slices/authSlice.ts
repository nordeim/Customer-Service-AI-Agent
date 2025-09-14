import { createSlice, PayloadAction, createAsyncThunk } from '@reduxjs/toolkit'
import { UserProfile, AuthTokens, User, AppError } from '@/types'
import apiClient from '@/services/api'
import wsManager from '@/services/websocket'

interface AuthState {
  user: User | null
  tokens: AuthTokens | null
  isAuthenticated: boolean
  isLoading: boolean
  error: AppError | null
  permissions: string[]
}

const initialState: AuthState = {
  user: null,
  tokens: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  permissions: [],
}

// Async thunks
export const login = createAsyncThunk(
  'auth/login',
  async ({ email, password }: { email: string; password: string }, { rejectWithValue }) => {
    try {
      const profile = await apiClient.login(email, password)
      
      // Set auth tokens in API client
      apiClient.setAuthTokens(profile.tokens)
      
      // Connect WebSocket with auth token
      wsManager.connect(profile.tokens.access_token)
      
      return profile
    } catch (error) {
      return rejectWithValue(error)
    }
  }
)

export const logout = createAsyncThunk(
  'auth/logout',
  async (_, { rejectWithValue }) => {
    try {
      await apiClient.logout()
      wsManager.disconnect()
      apiClient.clearAuth()
    } catch (error) {
      return rejectWithValue(error)
    }
  }
)

export const refreshToken = createAsyncThunk(
  'auth/refreshToken',
  async (_, { getState, rejectWithValue }) => {
    const state = getState() as { auth: AuthState }
    const refreshToken = state.auth.tokens?.refresh_token
    
    if (!refreshToken) {
      throw new Error('No refresh token available')
    }
    
    try {
      const tokens = await apiClient.refreshToken(refreshToken)
      apiClient.setAuthTokens(tokens)
      return tokens
    } catch (error) {
      return rejectWithValue(error)
    }
  }
)

export const getProfile = createAsyncThunk(
  'auth/getProfile',
  async (_, { rejectWithValue }) => {
    try {
      const profile = await apiClient.getProfile()
      return profile
    } catch (error) {
      return rejectWithValue(error)
    }
  }
)

export const updateProfile = createAsyncThunk(
  'auth/updateProfile',
  async (updates: Partial<User>, { rejectWithValue }) => {
    try {
      if (!updates.id) throw new Error('User ID required')
      const user = await apiClient.updateUser(updates.id, updates)
      return user
    } catch (error) {
      return rejectWithValue(error)
    }
  }
)

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setUser: (state, action: PayloadAction<User>) => {
      state.user = action.payload
    },
    setTokens: (state, action: PayloadAction<AuthTokens>) => {
      state.tokens = action.payload
      state.isAuthenticated = true
      apiClient.setAuthTokens(action.payload)
    },
    clearAuth: (state) => {
      state.user = null
      state.tokens = null
      state.isAuthenticated = false
      state.permissions = []
      apiClient.clearAuth()
      wsManager.disconnect()
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload
    },
    clearError: (state) => {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      // Login
      .addCase(login.pending, (state) => {
        state.isLoading = true
        state.error = null
      })
      .addCase(login.fulfilled, (state, action) => {
        state.user = action.payload.user
        state.tokens = action.payload.tokens
        state.permissions = action.payload.permissions
        state.isAuthenticated = true
        state.isLoading = false
        state.error = null
      })
      .addCase(login.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload as AppError
        state.isAuthenticated = false
      })
      // Logout
      .addCase(logout.pending, (state) => {
        state.isLoading = true
      })
      .addCase(logout.fulfilled, (state) => {
        state.user = null
        state.tokens = null
        state.permissions = []
        state.isAuthenticated = false
        state.isLoading = false
        state.error = null
      })
      .addCase(logout.rejected, (state, action) => {
        state.isLoading = false
        state.error = action.payload as AppError
        // Still clear auth data even if logout fails
        state.user = null
        state.tokens = null
        state.permissions = []
        state.isAuthenticated = false
      })
      // Refresh token
      .addCase(refreshToken.fulfilled, (state, action) => {
        state.tokens = action.payload
        apiClient.setAuthTokens(action.payload)
      })
      .addCase(refreshToken.rejected, (state, action) => {
        state.error = action.payload as AppError
        // If refresh fails, user needs to re-authenticate
        state.isAuthenticated = false
        state.user = null
        state.tokens = null
        state.permissions = []
      })
      // Get profile
      .addCase(getProfile.fulfilled, (state, action) => {
        state.user = action.payload.user
        state.permissions = action.payload.permissions
        state.isAuthenticated = true
      })
      .addCase(getProfile.rejected, (state, action) => {
        state.error = action.payload as AppError
        // If we can't get profile, we're not authenticated
        state.isAuthenticated = false
      })
      // Update profile
      .addCase(updateProfile.fulfilled, (state, action) => {
        state.user = action.payload
      })
      .addCase(updateProfile.rejected, (state, action) => {
        state.error = action.payload as AppError
      })
  },
})

export const { setUser, setTokens, clearAuth, setLoading, clearError } = authSlice.actions

// Selectors
export const selectUser = (state: { auth: AuthState }) => state.auth.user
export const selectIsAuthenticated = (state: { auth: AuthState }) => state.auth.isAuthenticated
export const selectAuthLoading = (state: { auth: AuthState }) => state.auth.isLoading
export const selectAuthError = (state: { auth: AuthState }) => state.auth.error
export const selectPermissions = (state: { auth: AuthState }) => state.auth.permissions
export const selectUserOrganization = (state: { auth: AuthState }) => state.auth.user?.organization_id

export default authSlice.reducer
