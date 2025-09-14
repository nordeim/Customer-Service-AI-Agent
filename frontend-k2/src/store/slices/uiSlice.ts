import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { UIState, Notification, A11yPreferences } from '@/types'

interface UIStateExtended extends UIState {
  sidebarOpen: boolean;
  mobileMenuOpen: boolean;
  modalStack: string[];
  toastQueue: Notification[];
  isScrolling: boolean;
  scrollPosition: number;
  viewportSize: {
    width: number;
    height: number;
    isMobile: boolean;
    isTablet: boolean;
    isDesktop: boolean;
  };
  connectionStatus: 'online' | 'offline' | 'connecting';
  performanceMode: 'high' | 'balanced' | 'low';
}

const initialState: UIStateExtended = {
  theme: 'light',
  language: 'en',
  rtl: false,
  sidebarOpen: false,
  mobileMenuOpen: false,
  notifications: [],
  loading: false,
  error: null,
  modalStack: [],
  toastQueue: [],
  isScrolling: false,
  scrollPosition: 0,
  viewportSize: {
    width: typeof window !== 'undefined' ? window.innerWidth : 1200,
    height: typeof window !== 'undefined' ? window.innerHeight : 800,
    isMobile: false,
    isTablet: false,
    isDesktop: true,
  },
  connectionStatus: 'online',
  performanceMode: 'balanced',
  accessibility: {
    reducedMotion: false,
    highContrast: false,
    largeText: false,
    screenReaderOptimized: false,
    keyboardNavigation: false,
    focusIndicators: true,
  },
}

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setTheme: (state, action: PayloadAction<'light' | 'dark' | 'auto'>) => {
      state.theme = action.payload
      // Apply theme to document
      if (typeof document !== 'undefined') {
        document.documentElement.classList.remove('light', 'dark')
        if (action.payload === 'auto') {
          const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
          document.documentElement.classList.add(prefersDark ? 'dark' : 'light')
        } else {
          document.documentElement.classList.add(action.payload)
        }
      }
    },
    setLanguage: (state, action: PayloadAction<string>) => {
      state.language = action.payload
      // Set RTL based on language
      const rtlLanguages = ['ar', 'he', 'fa', 'ur']
      state.rtl = rtlLanguages.includes(action.payload)
      
      // Apply RTL to document
      if (typeof document !== 'undefined') {
        document.documentElement.setAttribute('lang', action.payload)
        document.documentElement.setAttribute('dir', state.rtl ? 'rtl' : 'ltr')
      }
    },
    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.sidebarOpen = action.payload
    },
    setMobileMenuOpen: (state, action: PayloadAction<boolean>) => {
      state.mobileMenuOpen = action.payload
    },
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen
    },
    toggleMobileMenu: (state) => {
      state.mobileMenuOpen = !state.mobileMenuOpen
    },
    addNotification: (state, action: PayloadAction<Notification>) => {
      state.notifications.unshift(action.payload)
      // Limit notifications to prevent memory issues
      if (state.notifications.length > 50) {
        state.notifications = state.notifications.slice(0, 50)
      }
    },
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(n => n.id !== action.payload)
    },
    markNotificationAsRead: (state, action: PayloadAction<string>) => {
      const notification = state.notifications.find(n => n.id === action.payload)
      if (notification) {
        notification.read = true
      }
    },
    markAllNotificationsAsRead: (state) => {
      state.notifications.forEach(n => n.read = true)
    },
    clearNotifications: (state) => {
      state.notifications = []
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload
    },
    clearError: (state) => {
      state.error = null
    },
    pushModal: (state, action: PayloadAction<string>) => {
      state.modalStack.push(action.payload)
    },
    popModal: (state) => {
      state.modalStack.pop()
    },
    clearModals: (state) => {
      state.modalStack = []
    },
    setScrollPosition: (state, action: PayloadAction<number>) => {
      state.scrollPosition = action.payload
    },
    setIsScrolling: (state, action: PayloadAction<boolean>) => {
      state.isScrolling = action.payload
    },
    setViewportSize: (state, action: PayloadAction<{ width: number; height: number }>) => {
      const { width, height } = action.payload
      state.viewportSize = {
        width,
        height,
        isMobile: width < 768,
        isTablet: width >= 768 && width < 1024,
        isDesktop: width >= 1024,
      }
    },
    setConnectionStatus: (state, action: PayloadAction<'online' | 'offline' | 'connecting'>) => {
      state.connectionStatus = action.payload
    },
    setPerformanceMode: (state, action: PayloadAction<'high' | 'balanced' | 'low'>) => {
      state.performanceMode = action.payload
    },
    setAccessibilityPreference: (state, action: PayloadAction<Partial<A11yPreferences>>) => {
      state.accessibility = { ...state.accessibility, ...action.payload }
      
      // Apply accessibility preferences
      if (typeof document !== 'undefined') {
        // Reduced motion
        if (action.payload.reducedMotion !== undefined) {
          document.documentElement.style.setProperty(
            'scroll-behavior', 
            action.payload.reducedMotion ? 'auto' : 'smooth'
          )
        }
        
        // High contrast
        if (action.payload.highContrast !== undefined) {
          document.documentElement.classList.toggle('high-contrast', action.payload.highContrast)
        }
        
        // Large text
        if (action.payload.largeText !== undefined) {
          document.documentElement.classList.toggle('large-text', action.payload.largeText)
        }
        
        // Focus indicators
        if (action.payload.focusIndicators !== undefined) {
          document.documentElement.classList.toggle('focus-visible', action.payload.focusIndicators)
        }
      }
    },
    toggleAccessibilityPreference: (state, action: PayloadAction<keyof A11yPreferences>) => {
      const key = action.payload
      state.accessibility[key] = !state.accessibility[key]
      
      // Apply the change immediately
      if (typeof document !== 'undefined') {
        switch (key) {
          case 'reducedMotion':
            document.documentElement.style.setProperty(
              'scroll-behavior', 
              state.accessibility.reducedMotion ? 'auto' : 'smooth'
            )
            break
          case 'highContrast':
            document.documentElement.classList.toggle('high-contrast', state.accessibility.highContrast)
            break
          case 'largeText':
            document.documentElement.classList.toggle('large-text', state.accessibility.largeText)
            break
          case 'focusIndicators':
            document.documentElement.classList.toggle('focus-visible', state.accessibility.focusIndicators)
            break
        }
      }
    },
    queueToast: (state, action: PayloadAction<Notification>) => {
      state.toastQueue.push(action.payload)
    },
    dequeueToast: (state) => {
      state.toastQueue.shift()
    },
    clearToastQueue: (state) => {
      state.toastQueue = []
    },
  },
})

// Actions
export const {
  setTheme,
  setLanguage,
  setSidebarOpen,
  setMobileMenuOpen,
  toggleSidebar,
  toggleMobileMenu,
  addNotification,
  removeNotification,
  markNotificationAsRead,
  markAllNotificationsAsRead,
  clearNotifications,
  setLoading,
  setError,
  clearError,
  pushModal,
  popModal,
  clearModals,
  setScrollPosition,
  setIsScrolling,
  setViewportSize,
  setConnectionStatus,
  setPerformanceMode,
  setAccessibilityPreference,
  toggleAccessibilityPreference,
  queueToast,
  dequeueToast,
  clearToastQueue,
} = uiSlice.actions

// Selectors
export const selectTheme = (state: { ui: UIStateExtended }) => state.ui.theme
export const selectLanguage = (state: { ui: UIStateExtended }) => state.ui.language
export const selectRtl = (state: { ui: UIStateExtended }) => state.ui.rtl
export const selectSidebarOpen = (state: { ui: UIStateExtended }) => state.ui.sidebarOpen
export const selectMobileMenuOpen = (state: { ui: UIStateExtended }) => state.ui.mobileMenuOpen
export const selectNotifications = (state: { ui: UIStateExtended }) => state.ui.notifications
export const selectUnreadNotifications = (state: { ui: UIStateExtended }) => 
  state.ui.notifications.filter(n => !n.read)
export const selectIsLoading = (state: { ui: UIStateExtended }) => state.ui.loading
export const selectError = (state: { ui: UIStateExtended }) => state.ui.error
export const selectModalStack = (state: { ui: UIStateExtended }) => state.ui.modalStack
export const selectViewportSize = (state: { ui: UIStateExtended }) => state.ui.viewportSize
export const selectIsMobile = (state: { ui: UIStateExtended }) => state.ui.viewportSize.isMobile
export const selectConnectionStatus = (state: { ui: UIStateExtended }) => state.ui.connectionStatus
export const selectPerformanceMode = (state: { ui: UIStateExtended }) => state.ui.performanceMode
export const selectAccessibility = (state: { ui: UIStateExtended }) => state.ui.accessibility
export const selectToastQueue = (state: { ui: UIStateExtended }) => state.ui.toastQueue

// Memoized selectors
export const selectHasActiveModal = (state: { ui: UIStateExtended }) => state.ui.modalStack.length > 0
export const selectTopModal = (state: { ui: UIStateExtended }) => state.ui.modalStack[state.ui.modalStack.length - 1]
export const selectNotificationCount = (state: { ui: UIStateExtended }) => state.ui.notifications.length
export const selectUnreadNotificationCount = (state: { ui: UIStateExtended }) => 
  state.ui.notifications.filter(n => !n.read).length

export default uiSlice.reducer
