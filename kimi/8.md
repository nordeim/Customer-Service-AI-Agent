<think>
Looking at this comprehensive request, I need to:

1. First understand what Phase 8 of the Coding Execution Plan v3 entails
2. Analyze the current codebase to understand what's already implemented
3. Create a meticulous plan for implementing Phase 8 frontend components
4. Ensure compliance with PRD v4 and Database Schema v4
5. Generate each file systematically with validation

Let me start by understanding Phase 8 requirements from the Coding Execution Plan v3.

From my analysis of the documents, Phase 8 is:
**Phase 8: Frontend (React + TS)** - 7 days duration
- Frontend application with React + TypeScript
- Strict typing, responsive design, accessibility
- Storybook for component development
- Component and unit tests

The files specified are:
- frontend/{package.json, tsconfig.json, vite.config.ts, .env.example}
- frontend/src/components/Chat/{ChatWindow.tsx, MessageList.tsx, MessageInput.tsx, TypingIndicator.tsx}
- frontend/src/components/Layout/{Header.tsx, Sidebar.tsx}
- frontend/src/store/{index.ts, slices/{authSlice.ts, conversationSlice.ts, uiSlice.ts}}
- frontend/src/services/{api.ts, websocket.ts}
- frontend/src/hooks/{useChat.ts}

Now I need to analyze the current codebase to understand:
1. What's already implemented in the backend (Phases 1-7)
2. API endpoints available for frontend consumption
3. WebSocket infrastructure already in place
4. Data models that the frontend needs to interface with

From the file list, I can see:
- Complete backend infrastructure (API, WebSocket, services, models)
- Integration layers for channels, monitoring, auth
- Business logic and AI services
- Database models and repositories

I need to create a frontend that:
- Integrates with the existing WebSocket infrastructure
- Consumes the API endpoints properly
- Follows PRD v4 requirements for accessibility, responsiveness
- Implements proper TypeScript strict mode
- Has comprehensive testing
```</think>

# Phase 8 Frontend Implementation Plan

## Executive Summary

This document outlines a systematic approach to implement Phase 8 (Frontend - React + TypeScript) of the Coding Execution Plan v3. Based on meticulous analysis of the completed Phases 1-7 infrastructure and comprehensive review of PRD v4 requirements, this plan ensures full compliance with accessibility, performance, and technical specifications.

## Current Infrastructure Analysis

### Backend Capabilities (Phases 1-7 Completed)
From the codebase analysis, the following infrastructure is operational:

**API Layer:**
- FastAPI backend with comprehensive endpoints
- JWT authentication system
- Rate limiting and security middleware
- Conversation, message, and user management APIs

**WebSocket Infrastructure:**
- Real-time WebSocket manager with authentication
- Message handling and broadcasting
- Connection state management

**Data Models (Schema v4 Compliant):**
- Organizations, users, conversations, messages
- AI/ML integration with knowledge entries
- Analytics and audit trails
- Multi-tenant isolation with RLS

**Integration Layer:**
- Salesforce Service Cloud integration
- Multi-channel support (email, Slack, Teams, WhatsApp)
- External system integrations (Jira, ServiceNow, Zendesk)
- Monitoring and metrics collection

### PRD v4 Frontend Requirements
- WCAG 2.1 AA accessibility compliance
- Flesch Reading Ease >60 readability
- 50+ languages with RTL support
- Responsive design for web and mobile
- Sub-500ms response time for user interactions
- Real-time updates via WebSocket

## Implementation Strategy

### 1. Technology Stack Selection

**Core Technologies:**
- **React 18** with concurrent features for optimal performance
- **TypeScript 5.3+** in strict mode for type safety
- **Vite** for fast development and optimized builds
- **Redux Toolkit** for state management with TypeScript
- **React Query** for API data fetching and caching
- **Tailwind CSS** for responsive, utility-first styling
- **React Hook Form** for form handling and validation

**Development Tools:**
- **Storybook** for component development and documentation
- **Vitest** for unit testing with TypeScript support
- **React Testing Library** for component testing
- **Playwright** for end-to-end testing
- **ESLint + Prettier** for code quality and formatting

### 2. Architecture Design

```
Frontend Architecture
├── Public Interface (Web/Mobile)
│   ├── Chat Components
│   │   ├── ChatWindow (Main container)
│   │   ├── MessageList (Message display)
│   │   ├── MessageInput (User input)
│   │   └── TypingIndicator (AI feedback)
│   ├── Layout Components
│   │   ├── Header (Navigation/branding)
│   │   └── Sidebar (Contextual info)
│   └── Accessibility Layer
│       ├── WCAG 2.1 AA compliance
│       ├── Screen reader support
│       ├── Keyboard navigation
│       └── RTL language support
├── State Management
│   ├── Redux Store
│   │   ├── Auth Slice (User/session)
│   │   ├── Conversation Slice (Chat state)
│   │   └── UI Slice (Interface state)
│   └── React Query (Server state)
├── Services
│   ├── API Client (RESTful calls)
│   ├── WebSocket Manager (Real-time)
│   └── Analytics (Usage tracking)
├── Hooks
│   ├── useChat (Chat logic)
│   ├── useAuth (Authentication)
│   └── useWebSocket (Real-time)
└── Infrastructure
    ├── Build optimization
    ├── Performance monitoring
    └── Error boundaries
```

### 3. File-by-File Implementation Plan

## Step-by-Step Implementation

### Step 1: Frontend Infrastructure Setup

<write_to_file>
<path>frontend/package.json</path>
<content>
{
  "name": "ai-customer-service-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest --coverage",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "lint:fix": "eslint . --ext ts,tsx --fix",
    "format": "prettier --write \"src/**/*.{ts,tsx,js,jsx,json,css,md}\"",
    "storybook": "storybook dev -p 6006",
    "build-storybook": "storybook build",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-redux": "^9.1.0",
    "@reduxjs/toolkit": "^2.2.0",
    "@tanstack/react-query": "^5.24.0",
    "react-hook-form": "^7.50.0",
    "@hookform/resolvers": "^3.3.0",
    "zod": "^3.22.0",
    "axios": "^1.6.0",
    "socket.io-client": "^4.7.0",
    "date-fns": "^3.3.0",
    "clsx": "^2.1.0",
    "react-intersection-observer": "^9.8.0",
    "react-hot-toast": "^2.4.0",
    "@headlessui/react": "^1.7.0",
    "@heroicons/react": "^2.1.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.56",
    "@types/react-dom": "^18.2.19",
    "@typescript-eslint/eslint-plugin": "^7.0.0",
    "@typescript-eslint/parser": "^7.0.0",
    "@vitejs/plugin-react": "^4.2.0",
    "autoprefixer": "^10.4.0",
    "eslint": "^8.56.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.5",
    "eslint-plugin-jsx-a11y": "^6.8.0",
    "postcss": "^8.4.0",
    "prettier": "^3.2.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.3.0",
    "vite": "^5.1.0",
    "vite-plugin-pwa": "^0.19.0",
    "vitest": "^1.3.0",
    "@vitest/ui": "^1.3.0",
    "@testing-library/react": "^14.2.0",
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/user-event": "^14.5.0",
    "jsdom": "^24.0.0",
    "@storybook/react": "^7.6.0",
    "@storybook/react-vite": "^7.6.0",
    "@storybook/addon-essentials": "^7.6.0",
    "@storybook/addon-interactions": "^7.6.0",
    "@storybook/addon-links": "^7.6.0",
    "@storybook/addon-onboarding": "^1.0.0",
    "@storybook/blocks": "^7.6.0",
    "@storybook/testing-library": "^0.2.0",
    "storybook": "^7.6.0"
  },
  "engines": {
    "node": ">=18.0.0",
    "npm": ">=9.0.0"
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}
</content>
</write_to_file>

<write_to_file>
<path>frontend/tsconfig.json</path>
<content>
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,

    /* Path mapping */
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@/components/*": ["src/components/*"],
      "@/services/*": ["src/services/*"],
      "@/store/*": ["src/store/*"],
      "@/hooks/*": ["src/hooks/*"],
      "@/utils/*": ["src/utils/*"],
      "@/types/*": ["src/types/*"]
    },

    /* Additional strict type checking */
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true,
    "noImplicitAny": true,
    "alwaysStrict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true,

    /* Module resolution */
    "allowSyntheticDefaultImports": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,

    /* Advanced */
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "removeComments": false,
    "incremental": true,
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo"
  },
  "include": ["src", "vite.config.ts", ".storybook"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
</content>
</write_to_file>

<write_to_file>
<path>frontend/tsconfig.node.json</path>
<content>
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "types": ["vite/client", "node"]
  },
  "include": ["vite.config.ts", "vitest.config.ts", ".storybook/main.ts"]
}
</content>
</write_to_file>

<write_to_file>
<path>frontend/vite.config.ts</path>
<content>
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { VitePWA } from 'vite-plugin-pwa'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'masked-icon.svg'],
      manifest: {
        name: 'AI Customer Service',
        short_name: 'AI-CS',
        description: 'AI-powered customer service for Salesforce',
        theme_color: '#ffffff',
        background_color: '#ffffff',
        display: 'standalone',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ]
      }
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@/components': path.resolve(__dirname, './src/components'),
      '@/services': path.resolve(__dirname, './src/services'),
      '@/store': path.resolve(__dirname, './src/store'),
      '@/hooks': path.resolve(__dirname, './src/hooks'),
      '@/utils': path.resolve(__dirname, './src/utils'),
      '@/types': path.resolve(__dirname, './src/types')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      },
      '/ws': {
        target: process.env.VITE_WS_URL || 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
        secure: false
      }
    }
  },
  build: {
    target: 'es2020',
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'redux-vendor': ['react-redux', '@reduxjs/toolkit'],
          'query-vendor': ['@tanstack/react-query'],
          'ui-vendor': ['@headlessui/react', '@heroicons/react']
        }
      }
    }
  },
  optimizeDeps: {
    esbuildOptions: {
      target: 'es2020'
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true
  }
})
</content>
</write_to_file>

<write_to_file>
<path>frontend/.env.example</path>
<content>
# API Configuration
VITE_API_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/ws

# Authentication
VITE_AUTH_DOMAIN=your-auth0-domain.auth0.com
VITE_AUTH_CLIENT_ID=your-auth0-client-id
VITE_AUTH_AUDIENCE=your-api-audience

# Features
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_NOTIFICATIONS=true
VITE_ENABLE_OFFLINE=true

# Performance
VITE_MESSAGE_BATCH_SIZE=50
VITE_TYPING_INDICATOR_DELAY=1000
VITE_AUTO_REFRESH_INTERVAL=30000

# UI Configuration
VITE_DEFAULT_THEME=light
VITE_DEFAULT_LANGUAGE=en
VITE_ENABLE_RTL=true
VITE_MAX_FILE_SIZE=10485760
VITE_SUPPORTED_FILE_TYPES=jpg,jpeg,png,gif,pdf,doc,docx,txt

# Development
VITE_ENABLE_MOCK_DATA=false
VITE_LOG_LEVEL=info
VITE_ENABLE_REACT_QUERY_DEVTOOLS=true
</content>
</write_to_file>

<write_to_file>
<path>frontend/tailwind.config.js</path>
<content>
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./.storybook/**/*.{js,ts,jsx,tsx}"
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
        secondary: {
          50: '#fdf2f8',
          100: '#fce7f3',
          200: '#fbcfe8',
          300: '#f9a8d4',
          400: '#f472b6',
          500: '#ec4899',
          600: '#db2777',
          700: '#be185d',
          800: '#9d174d',
          900: '#831843',
        },
        success: {
          50: '#f0fdf4',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
        },
        warning: {
          50: '#fffbeb',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
        },
        error: {
          50: '#fef2f2',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
        },
        gray: {
          50: '#f9fafb',
          100: '#f3f4f6',
          200: '#e5e7eb',
          300: '#d1d5db',
          400: '#9ca3af',
          500: '#6b7280',
          600: '#4b5563',
          700: '#374151',
          800: '#1f2937',
          900: '#111827',
        }
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'Noto Sans', 'sans-serif'],
        mono: ['Fira Code', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'Liberation Mono', 'Courier New', 'monospace'],
      },
      fontSize: {
        'xs': ['0.75rem', { lineHeight: '1rem' }],
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'base': ['1rem', { lineHeight: '1.5rem' }],
        'lg': ['1.125rem', { lineHeight: '1.75rem' }],
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'typing': 'typing 1.5s infinite',
        'bounce-light': 'bounce 1s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        typing: {
          '0%, 60%, 100%': { opacity: '1' },
          '30%': { opacity: '0.3' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
      borderRadius: {
        '4xl': '2rem',
      },
      boxShadow: {
        'soft': '0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 10px 20px -2px rgba(0, 0, 0, 0.04)',
        'medium': '0 4px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
        'strong': '0 10px 40px -10px rgba(0, 0, 0, 0.15), 0 2px 8px 0px rgba(0, 0, 0, 0.06)',
      },
      zIndex: {
        '60': '60',
        '70': '70',
        '80': '80',
        '90': '90',
        '100': '100',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/aspect-ratio'),
  ],
}
</content>
</write_to_file>

<write_to_file>
<path>frontend/postcss.config.js</path>
<content>
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
</content>
</write_to_file>

### Step 2: Type Definitions and Core Setup

<write_to_file>
<path>frontend/src/types/index.ts</path>
<content>
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
</content>
</write_to_file>

<write_to_file>
<path>frontend/src/test/setup.ts</path>
<content>
import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

// Cleanup after each test
afterEach(() => {
  cleanup()
})

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
  takeRecords() {
    return []
  }
}

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
}

// Mock WebSocket
class MockWebSocket {
  constructor(url: string) {
    this.url = url
    this.readyState = WebSocket.CONNECTING
    setTimeout(() => {
      this.readyState = WebSocket.OPEN
      this.onopen?.(new Event('open'))
    }, 0)
  }

  url: string
  readyState: number
  onopen: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null

  send(data: string) {
    setTimeout(() => {
      this.onmessage?.(new MessageEvent('message', { data }))
    }, 0)
  }

  close() {
    this.readyState = WebSocket.CLOSED
    this.onclose?.(new CloseEvent('close'))
  }
}

global.WebSocket = MockWebSocket as any

// Mock window.HTMLElement
global.HTMLElement = class HTMLElement {
  constructor() {}
  attachShadow() {
    return { mode: 'open' }
  }
  addEventListener() {}
  removeEventListener() {}
  dispatchEvent() {
    return true
  }
  getAttribute() {
    return null
  }
  setAttribute() {}
  removeAttribute() {}
  hasAttribute() {
    return false
  }
  querySelector() {
    return null
  }
  querySelectorAll() {
    return []
  }
  getBoundingClientRect() {
    return {
      top: 0,
      left: 0,
      bottom: 0,
      right: 0,
      width: 0,
      height: 0,
      x: 0,
      y: 0,
    }
  }
}

// Mock crypto.randomUUID
if (!global.crypto) {
  global.crypto = {} as any
}
if (!global.crypto.randomUUID) {
  global.crypto.randomUUID = () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = (Math.random() * 16) | 0
      const v = c === 'x' ? r : (r & 0x3) | 0x8
      return v.toString(16)
    })
  }
}

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn()

// Mock console methods to reduce noise in tests
global.console = {
  ...console,
  warn: vi.fn(),
  error: vi.fn(),
}

// Set up mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
}

global.localStorage = localStorageMock as any

// Set up mock sessionStorage
const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
}

global.sessionStorage = sessionStorageMock as any
</content>
</write_to_file>

### Step 3: Core Services Implementation

<write_to_file>
<path>frontend/src/services/api.ts</path>
<content>
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
</content>
</write_to_file>

<write_to_file>
<path>frontend/src/services/websocket.ts</path>
<content>
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
</content>
</write_to_file>

### Step 4: Redux Store Setup

<write_to_file>
<path>frontend/src/store/index.ts</path>
<content>
import { configureStore } from '@reduxjs/toolkit'
import { setupListeners } from '@reduxjs/toolkit/query'
import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux'
import authSlice from './slices/authSlice'
import conversationSlice from './slices/conversationSlice'
import uiSlice from './slices/uiSlice'

// Configure the store
export const store = configureStore({
  reducer: {
    auth: authSlice,
    conversation: conversationSlice,
    ui: uiSlice,
  },
  // Enable Redux DevTools in development
  devTools: process.env.NODE_ENV !== 'production',
  // Custom middleware configuration
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types
        ignoredActions: ['persist/PERSIST'],
        // Ignore these field paths in all actions
        ignoredActionPaths: ['meta.arg', 'payload.timestamp'],
        // Ignore these paths in the state
        ignoredPaths: ['items.dates'],
      },
      // Enable immutable check
      immutableCheck: {
        ignoredPaths: ['items.data'],
      },
    }),
})

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch

// Typed hooks for use throughout the app
export const useAppDispatch = () => useDispatch<AppDispatch>()
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector

// Set up listeners for RTK Query
setupListeners(store.dispatch)

export default store
</content>
</write_to_file>

<write_to_file>
<path>frontend/src/store/slices/authSlice.ts</path>
<content>
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
</content>
</write_to_file>

<write_to_file>
<path>frontend/src/store/slices/conversationSlice.ts</path>
<content>
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
      
     
