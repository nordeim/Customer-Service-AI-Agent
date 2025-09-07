<think>
I need to continue with the same rigorous approach for the remaining Phase 8 files. Let me systematically work through:

1. React application structure (App.tsx, components)
2. Redux store setup with TypeScript
3. Service layers (API, WebSocket)
4. Hooks and utilities
5. Tests and stories

I'll ensure each file complies with:
- PRD v4 accessibility requirements (WCAG 2.1 AA)
- TypeScript strict mode
- Database Schema v4 compatibility
- Evidence-based implementation with proper error handling
- Security best practices
- Performance optimizations

Let me continue methodically.
</think>

Continuing with Phase 8 implementation - React application core:

## frontend/src/App.tsx
```typescript
import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { Toaster } from '@components/Toast/Toaster';
import { Header } from '@components/Layout/Header';
import { Sidebar } from '@components/Layout/Sidebar';
import { ChatWindow } from '@components/Chat/ChatWindow';
import { LoginPage } from '@components/Auth/LoginPage';
import { Dashboard } from '@components/Dashboard/Dashboard';
import { AdminPanel } from '@components/Admin/AdminPanel';
import { UserSettings } from '@components/User/UserSettings';
import { LoadingSpinner } from '@components/UI/LoadingSpinner';
import { useAuth } from '@hooks/useAuth';
import { useWebSocket } from '@hooks/useWebSocket';
import { RootState } from '@store/types';
import { AccessibilityAnnouncer } from '@components/Accessibility/AccessibilityAnnouncer';
import { ErrorBoundary } from '@components/Error/ErrorBoundary';
import { KeyboardShortcuts } from '@components/Accessibility/KeyboardShortcuts';
import { ThemeToggle } from '@components/Theme/ThemeToggle';
import { NotificationHandler } from '@components/Notification/NotificationHandler';
import './App.css';

const App: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const { isConnected } = useWebSocket();
  const { theme, fontSize, reducedMotion } = useSelector((state: RootState) => state.ui.accessibility);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen" role="status" aria-live="polite">
        <LoadingSpinner size="large" />
        <span className="sr-only">Loading application...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <ErrorBoundary>
        <div className="min-h-screen bg-background flex items-center justify-center">
          <LoginPage />
          <Toaster />
          <AccessibilityAnnouncer />
        </div>
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary>
      <div 
        className="min-h-screen bg-background text-foreground"
        data-theme={theme}
        data-font-size={fontSize}
        data-reduced-motion={reducedMotion}
      >
        <NotificationHandler />
        <KeyboardShortcuts />
        <AccessibilityAnnouncer />
        
        <Header />
        
        <div className="flex h-[calc(100vh-4rem)]">
          <Sidebar />
          
          <main className="flex-1 overflow-hidden" role="main" aria-label="Main content">
            <Routes>
              <Route path="/" element={<ChatWindow />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/admin" element={<AdminPanel />} />
              <Route path="/settings" element={<UserSettings />} />
              <Route path="/chat/:conversationId" element={<ChatWindow />} />
            </Routes>
          </main>
        </div>
        
        <div className="fixed bottom-4 right-4 flex flex-col gap-2">
          <ThemeToggle />
          <div className="text-xs text-muted-foreground bg-background/80 backdrop-blur-sm rounded-lg p-2">
            Status: {isConnected ? 'Connected' : 'Reconnecting...'}
          </div>
        </div>
        
        <Toaster />
      </div>
    </ErrorBoundary>
  );
};

export default App;
```

## frontend/src/App.css
```css
/* App-specific styles */
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-header {
  flex-shrink: 0;
}

.app-main {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.app-content {
  flex: 1;
  overflow-y: auto;
  position: relative;
}

/* Responsive design */
@media (max-width: 768px) {
  .app-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    height: 100vh;
    width: 280px;
    z-index: 50;
    transform: translateX(-100%);
    transition: transform 0.3s ease-in-out;
  }
  
  .app-sidebar.open {
    transform: translateX(0);
  }
  
  .app-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    z-index: 40;
    opacity: 0;
    visibility: hidden;
    transition: opacity 0.3s ease-in-out, visibility 0.3s ease-in-out;
  }
  
  .app-overlay.visible {
    opacity: 1;
    visibility: visible;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .app-container {
    border: 2px solid currentColor;
  }
  
  .app-header {
    border-bottom: 3px solid currentColor;
  }
  
  .app-sidebar {
    border-right: 3px solid currentColor;
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  .app-sidebar {
    transition: none;
  }
  
  .app-overlay {
    transition: none;
  }
}

/* Focus management */
.app-main:focus {
  outline: none;
}

.app-main:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: -2px;
}

/* Loading states */
.app-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background-color: var(--color-background);
}

.app-loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid var(--color-neutral-200);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Error states */
.app-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 2rem;
  text-align: center;
}

.app-error-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--color-error);
  margin-bottom: 0.5rem;
}

.app-error-message {
  color: var(--color-text-secondary);
  margin-bottom: 1rem;
}

.app-error-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

/* Status indicators */
.app-status {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  z-index: 50;
}

.app-status-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background-color: var(--color-surface);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--border-radius-md);
  font-size: 0.875rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.app-status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--color-neutral-400);
}

.app-status-indicator.connected {
  background-color: var(--color-success);
}

.app-status-indicator.disconnected {
  background-color: var(--color-error);
}

.app-status-indicator.reconnecting {
  background-color: var(--color-warning);
  animation: pulse 2s infinite;
}

/* Theme toggle */
.app-theme-toggle {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  z-index: 50;
}

/* Keyboard shortcuts */
.app-keyboard-shortcuts {
  position: fixed;
  bottom: 4rem;
  right: 1rem;
  z-index: 50;
}

/* Responsive utilities */
.app-hidden-mobile {
  display: block;
}

.app-visible-mobile {
  display: none;
}

@media (max-width: 768px) {
  .app-hidden-mobile {
    display: none;
  }
  
  .app-visible-mobile {
    display: block;
  }
}

/* Print styles */
@media print {
  .app-status,
  .app-theme-toggle,
  .app-keyboard-shortcuts {
    display: none;
  }
}
```

## frontend/src/i18n.ts
```typescript
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import Backend from 'i18next-http-backend';

// Import translation files
import enCommon from './locales/en/common.json';
import enChat from './locales/en/chat.json';
import enErrors from './locales/en/errors.json';
import enValidation from './locales/en/validation.json';

import esCommon from './locales/es/common.json';
import esChat from './locales/es/chat.json';
import esErrors from './locales/es/errors.json';
import esValidation from './locales/es/validation.json';

// Import RTL language support
import 'intl-pluralrules';

// Language resources
const resources = {
  en: {
    common: enCommon,
    chat: enChat,
    errors: enErrors,
    validation: enValidation,
  },
  es: {
    common: esCommon,
    chat: esChat,
    errors: esErrors,
    validation: esValidation,
  },
};

// i18n configuration
i18n
  .use(Backend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    debug: process.env.NODE_ENV === 'development',
    
    interpolation: {
      escapeValue: false, // React already escapes
      format: (value, format, lng) => {
        if (format === 'uppercase') return value.toUpperCase();
        if (format === 'lowercase') return value.toLowerCase();
        if (format === 'capitalize') {
          return value.charAt(0).toUpperCase() + value.slice(1);
        }
        return value;
      },
    },
    
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng',
    },
    
    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
      addPath: '/locales/add/{{lng}}/{{ns}}',
      allowMultiLoading: false,
    },
    
    react: {
      useSuspense: true,
      transSupportBasicHtmlNodes: true,
      transKeepBasicHtmlNodesFor: ['br', 'strong', 'i'],
    },
    
    // Accessibility support
    accessibility: {
      // Ensure screen readers announce language changes
      announceLanguageChange: true,
    },
    
    // Pluralization rules
    pluralSeparator: '_',
    contextSeparator: '_',
    
    // Namespace configuration
    defaultNS: 'common',
    ns: ['common', 'chat', 'errors', 'validation'],
    
    // Post-processing for accessibility
    postProcess: ['a11y_text'],
    
    // Save missing translations
    saveMissing: process.env.NODE_ENV === 'development',
    saveMissingTo: 'all',
    missingKeyHandler: (lng, ns, key, fallbackValue) => {
      console.warn(`Missing translation: ${lng}.${ns}.${key}`);
    },
  });

// RTL language support
export const RTL_LANGUAGES = ['ar', 'he', 'fa', 'ur'];

export const isRTLLanguage = (language: string): boolean => {
  return RTL_LANGUAGES.includes(language);
};

// Language direction helper
export const getLanguageDirection = (language: string): 'ltr' | 'rtl' => {
  return isRTLLanguage(language) ? 'rtl' : 'ltr';
};

// Export configured instance
export default i18n;

// Type definitions for translations
export type TranslationKeys = {
  common: typeof enCommon;
  chat: typeof enChat;
  errors: typeof enErrors;
  validation: typeof enValidation;
};

declare module 'react-i18next' {
  interface CustomTypeOptions {
    resources: TranslationKeys;
  }
}
```

## frontend/src/store/index.ts
```typescript
import { configureStore } from '@reduxjs/toolkit';
import { persistStore, persistReducer, FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER } from 'redux-persist';
import storage from 'redux-persist/lib/storage';
import { authSlice } from './slices/authSlice';
import { conversationSlice } from './slices/conversationSlice';
import { uiSlice } from './slices/uiSlice';
import { notificationSlice } from './slices/notificationSlice';
import { websocketSlice } from './slices/websocketSlice';
import { api } from './api';
import { RootState, AppDispatch } from './types';

// Persistence configuration
const persistConfig = {
  key: 'root',
  version: 1,
  storage,
  whitelist: ['auth', 'ui'], // Only persist auth and UI state
  migrate: (state: any, version: number) => {
    // Migration logic for state versions
    if (state && state._persist && state._persist.version !== version) {
      console.log(`Migrating state from version ${state._persist.version} to ${version}`);
      // Add migration logic here as needed
    }
    return Promise.resolve(state);
  },
};

// Root reducer
const rootReducer = {
  auth: authSlice.reducer,
  conversation: conversationSlice.reducer,
  ui: uiSlice.reducer,
  notification: notificationSlice.reducer,
  websocket: websocketSlice.reducer,
  [api.reducerPath]: api.reducer,
};

// Store configuration
export const store = configureStore({
  reducer: rootReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [FLUSH, REHYDRATE, PAUSE, PERSIST, PURGE, REGISTER],
        ignoredActionPaths: ['meta.arg', 'payload.timestamp', 'payload.error'],
        ignoredPaths: ['items.dates'],
      },
      immutableCheck: {
        ignoredPaths: ['items.data'],
      },
    }).concat(api.middleware),
  devTools: process.env.NODE_ENV !== 'production',
  enhancers: (defaultEnhancers) => [
    ...defaultEnhancers,
    // Add custom enhancers here
  ],
});

// Persistor
export const persistor = persistStore(store);

// Export typed hooks
export type { RootState, AppDispatch };
export { useAppDispatch, useAppSelector } from './hooks';

// Export actions
export { authSlice } from './slices/authSlice';
export { conversationSlice } from './slices/conversationSlice';
export { uiSlice } from './slices/uiSlice';
export { notificationSlice } from './slices/notificationSlice';
export { websocketSlice } from './slices/websocketSlice';

// Export API
export { api } from './api';
export { useGetConversationsQuery, useGetMessagesQuery, useSendMessageMutation } from './api';

// Reset store function
export const resetStore = () => {
  persistor.pause();
  persistor.flush().then(() => {
    persistor.purge();
    store.dispatch({ type: 'RESET' });
  });
};

// Store subscription for debugging
if (process.env.NODE_ENV === 'development') {
  store.subscribe(() => {
    console.log('Store state:', store.getState());
  });
}
```

https://www.kimi.com/share/d2ul0e6an0vqnibhl0s0
