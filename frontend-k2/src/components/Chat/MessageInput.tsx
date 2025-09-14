import React, { useState, useRef, useCallback, KeyboardEvent, ChangeEvent, DragEvent } from 'react'
import { MessageContentType } from '@/types'
import { clsx } from 'clsx'
import toast from 'react-hot-toast'

interface MessageInputProps {
  conversationId: string
  onSendMessage: (content: string, contentType?: MessageContentType, files?: File[]) => void
  onFocus?: () => void
  onBlur?: () => void
  onChange?: (value: string) => void
  disabled?: boolean
  placeholder?: string
  maxLength?: number
  enableFileUpload?: boolean
  maxFileSize?: number
  acceptedFileTypes?: string[]
  className?: string
  ariaLabel?: string
}

interface FileUploadState {
  files: File[]
  isDragging: boolean
  isUploading: boolean
  uploadProgress: number
}

export const MessageInput: React.FC<MessageInputProps> = ({
  conversationId,
  onSendMessage,
  onFocus,
  onBlur,
  onChange,
  disabled = false,
  placeholder = 'Type your message...',
  maxLength = 4000,
  enableFileUpload = true,
  maxFileSize = 10 * 1024 * 1024, // 10MB
  acceptedFileTypes = ['image/*', 'text/*', 'application/pdf'],
  className,
  ariaLabel = 'Message input',
}) => {
  const [inputValue, setInputValue] = useState('')
  const [fileUpload, setFileUpload] = useState<FileUploadState>({
    files: [],
    isDragging: false,
    isUploading: false,
    uploadProgress: 0,
  })
  const inputRef = useRef<HTMLInputElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleInputChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    setInputValue(event.target.value)
    if (onChange) onChange(event.target.value)
  }, [onChange])

  const handleInputFocus = useCallback(() => {
    if (onFocus) onFocus()
  }, [onFocus])

  const handleInputBlur = useCallback(() => {
    if (onBlur) onBlur()
  }, [onBlur])

  const handleKeyDown = useCallback((event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSendMessage()
    }
  }, [])

  const handleSendMessage = useCallback(() => {
    if (disabled || !inputValue.trim()) return

    onSendMessage(inputValue, 'text', fileUpload.files)
    setInputValue('')
    setFileUpload({ ...fileUpload, files: [] })
  }, [disabled, inputValue, fileUpload.files, onSendMessage])

  const handleFileChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (files) {
      const newFiles = Array.from(files)
      setFileUpload({ ...fileUpload, files: newFiles })
    }
  }, [fileUpload])

  const handleFileDrop = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    const files = event.dataTransfer.files
    if (files) {
      const newFiles = Array.from(files)
      setFileUpload({ ...fileUpload, files: newFiles, isDragging: false })
    }
  }, [fileUpload])

  const handleDragOver = useCallback((event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setFileUpload({ ...fileUpload, isDragging: true })
  }, [fileUpload])

  const handleDragLeave = useCallback(() => {
    setFileUpload({ ...fileUpload, isDragging: false })
  }, [fileUpload])

  const handleFileUpload = useCallback(async () => {
    if (!fileUpload.files.length) return

    setFileUpload({ ...fileUpload, isUploading: true, uploadProgress: 0 })

    try {
      for (let i = 0; i < fileUpload.files.length; i++) {
        const file = fileUpload.files[i]
        const uploadPromise = new Promise<number>((resolve, reject) => {
          const reader = new FileReader()
          reader.onload = () => {
            resolve(reader.result as number)
          }
          reader.onerror = () => {
            reject(reader.error)
          }
          reader.readAsDataURL(file)
        })

        const result = await uploadPromise
        setFileUpload(prev => ({
          ...prev,
          uploadProgress: Math.round(((i + 1) / fileUpload.files.length) * 100),
        }))
      }

      toast.success('Files uploaded successfully')
      setFileUpload({ ...fileUpload, isUploading: false, files: [] })
    } catch (error) {
      console.error('File upload failed:', error)
      toast.error('File upload failed')
      setFileUpload({ ...fileUpload, isUploading: false, files: [] })
    }
  }, [fileUpload])

  const handleFileUploadClick = useCallback(() => {
    if (fileInputRef.current) {
      fileInputRef.current.click()
    }
  }, [])

  const handleFileUploadClear = useCallback(() => {
    setFileUpload({ ...fileUpload, files: [] })
  }, [])

  const isInputDisabled = disabled || fileUpload.isUploading

  return (
    <div className={clsx('relative', className)}>
      {/* File Upload */}
      {enableFileUpload && (
        <div className="absolute inset-y-0 left-0 flex items-center pl-2">
          <label
            htmlFor="file-upload"
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer"
            aria-label="Upload file"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.401 4 4 0 018.8 0A4 4 0 017 16zm10-4a4 4 0 00-4-4 4 4 0 00-4 4 4 4 0 004 4 4 4 0 004-4z" />
            </svg>
          </label>
          <input
            id="file-upload"
            type="file"
            className="hidden"
            ref={fileInputRef}
            onChange={handleFileChange}
            multiple
            accept={acceptedFileTypes.join(',')}
          />
        </div>
      )}

      {/* Input */}
      <input
        type="text"
        value={inputValue}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onFocus={handleInputFocus}
        onBlur={handleInputBlur}
        disabled={isInputDisabled}
        placeholder={placeholder}
        maxLength={maxLength}
        className={clsx(
          'flex-1 bg-transparent border-none text-gray-900 dark:text-gray-100',
          'placeholder-gray-400 dark:placeholder-gray-500',
          'focus:ring-0 focus:outline-none',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'py-2 px-3',
          'rounded-lg',
          'text-sm',
          'w-full',
          'ring-1 ring-inset ring-gray-200 dark:ring-gray-700',
          'shadow-sm',
          'transition-all duration-200',
          'hover:ring-gray-300 dark:hover:ring-gray-600',
          'focus:ring-primary-500 dark:focus:ring-primary-400',
          'focus:ring-2',
          'focus:border-transparent',
          'focus:shadow-none',
          'focus:placeholder-transparent',
          'focus:text-gray-900 dark:focus:text-gray-100',
          'focus:bg-transparent',
          'focus:caret-primary-500 dark:focus:caret-primary-400',
          'focus:selection:bg-primary-100 dark:focus:selection:bg-primary-900',
          'focus:selection:text-primary-700 dark:focus:selection:text-primary-300',
          'focus:outline-none',
          'focus:ring-2',
          'focus:ring-primary-500 dark:focus:ring-primary-400',
          'focus:border-transparent',
          'focus:shadow-none',
          'focus:placeholder-transparent',
          'focus:text-gray-900 dark:focus:text-gray-100',
          'focus:bg-transparent',
          'focus:caret-primary-500 dark:focus:caret-primary-400',
          'focus:selection:bg-primary-100 dark:focus:selection:bg-primary-900',
          'focus:selection:text-primary-700 dark:focus:selection:text-primary-300',
          'focus:outline-none',
          'focus:ring-2',
          'focus:ring-primary-500 dark:focus:ring-primary-400',
          'focus:border-transparent',
          'focus:shadow-none',
          'focus:placeholder-transparent',
          'focus:text-gray-900 dark:focus:text-gray-100',
          'focus:bg-transparent',
          'focus:caret-primary-500 dark:focus:caret-primary-400',
          'focus:selection:bg-primary-100 dark:focus:selection:bg-primary-900',
          'focus:selection:text-primary-700 dark:focus:selection:text-primary-300',
          'focus:outline-none',
          'focus:ring-2',
          'focus:ring-primary-500 dark:focus:ring-primary-400',
          'focus:border-transparent',
          'focus:shadow-none',
          'focus:placeholder-transparent',
          'focus:text-gray-900 dark:focus:text-gray-100',
          'focus:bg-transparent',
          'focus:caret-primary-500 dark:focus:caret-primary-400',
          'focus:selection:bg-primary-100 dark:focus:selection:bg-primary-900',
          'focus:selection:text-primary-700 dark:focus:selection:text-primary-300',
          'focus:outline-none',
          'focus:ring-2',
          'focus:ring-primary-500 dark:focus:ring-primary-400
