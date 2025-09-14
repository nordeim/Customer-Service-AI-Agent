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
