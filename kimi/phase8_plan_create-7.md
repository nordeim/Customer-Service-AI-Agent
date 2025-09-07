<think>
I need to continue with the same rigorous approach. Let me systematically complete:

1. Remaining chat components (MessageInput, TypingIndicator, ChatHeader, etc.)
2. Core UI components
3. Layout components
4. Accessibility components
5. Essential utilities and hooks
6. Tests and configuration

Each file needs to:
- Comply with PRD v4 accessibility requirements (WCAG 2.1 AA)
- Use TypeScript strict mode
- Align with Database Schema v4
- Include proper error handling
- Follow security best practices
- Be evidence-based with clear implementation

Let me continue methodically with the remaining files.
</think>

Continuing with Phase 8 implementation - Remaining chat components and core files:

## frontend/src/components/Chat/MessageInput.tsx
```typescript
import React, { useState, useRef, useEffect, KeyboardEvent, ChangeEvent } from 'react';
import { Send, Paperclip, Smile, Mic, MicOff } from 'lucide-react';
import { Button } from '@components/UI/Button';
import { Textarea } from '@components/UI/Textarea';
import { FileUpload } from '@components/UI/FileUpload';
import { EmojiPicker } from '@components/UI/EmojiPicker';
import { cn } from '@utils/cn';
import { useTranslation } from 'react-i18next';
import { useAppSelector } from '@store/hooks';
import { VoiceRecorder } from '@components/UI/VoiceRecorder';
import { useKeyboardShortcuts } from '@hooks/useKeyboardShortcuts';
import type { RootState } from '@store/types';

interface MessageInputProps {
  onSendMessage: (content: string, contentType?: string) => void;
  onFileUpload?: (file: File) => void;
  disabled?: boolean;
  enterToSend?: boolean;
  placeholder?: string;
  maxLength?: number;
  className?: string;
  'aria-label'?: string;
}

export const MessageInput: React.FC<MessageInputProps> = ({
  onSendMessage,
  onFileUpload,
  disabled = false,
  enterToSend = true,
  placeholder = 'Type your message...',
  maxLength = 10000,
  className = '',
  'aria-label': ariaLabel,
}) => {
  const { t } = useTranslation();
  const { reducedMotion } = useAppSelector((state: RootState) => state.ui.accessibility);
  const [message, setMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [showFileUpload, setShowFileUpload] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Focus textarea on mount
  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      const textarea = textareaRef.current;
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`; // Max height 200px
    }
  }, [message]);

  // Handle message send
  const handleSend = async () => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage || disabled) return;

    try {
      await onSendMessage(trimmedMessage, 'text');
      setMessage('');
      
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  // Handle keyboard events
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter') {
      if (enterToSend && !event.shiftKey) {
        event.preventDefault();
        handleSend();
      } else if (!enterToSend && event.ctrlKey) {
        event.preventDefault();
        handleSend();
      }
    }
    
    if (event.key === 'Escape') {
      setShowEmojiPicker(false);
      setShowFileUpload(false);
    }
  };

  // Handle input change
  const handleChange = (event: ChangeEvent<HTMLTextareaElement>) => {
    const value = event.target.value;
    if (value.length <= maxLength) {
      setMessage(value);
    }
  };

  // Handle emoji selection
  const handleEmojiSelect = (emoji: string) => {
    setMessage(prev => prev + emoji);
    setShowEmojiPicker(false);
    textareaRef.current?.focus();
  };

  // Handle file selection
  const handleFileSelect = (files: FileList | null) => {
    if (!files || !onFileUpload) return;
    
    Array.from(files).forEach(file => {
      if (file.size > 10 * 1024 * 1024) { // 10MB limit
        alert(t('chat.fileTooLarge', { size: '10MB' }));
        return;
      }
      onFileUpload(file);
    });
    
    setShowFileUpload(false);
  };

  // Handle voice recording
  const handleVoiceRecording = (audioBlob: Blob) => {
    // Convert blob to base64 or upload to server
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64Audio = reader.result as string;
      onSendMessage(base64Audio, 'audio');
    };
    reader.readAsDataURL(audioBlob);
    setIsRecording(false);
  };

  // Keyboard shortcuts
  useKeyboardShortcuts({
    'ctrl+shift+e': () => setShowEmojiPicker(prev => !prev),
    'ctrl+shift+f': () => setShowFileUpload(prev => !prev),
    'ctrl+shift+r': () => setIsRecording(prev => !prev),
  });

  // Character count
  const characterCount = message.length;
  const isNearLimit = characterCount > maxLength * 0.9;

  return (
    <div
      ref={containerRef}
      className={cn(
        'relative border-t border-border bg-background',
        'p-4 space-y-3',
        className
      )}
      role="form"
      aria-label={ariaLabel || t('chat.messageInputLabel')}
    >
      {/* Input area */}
      <div className="flex items-end gap-3">
        {/* File upload button */}
        {onFileUpload && (
          <FileUpload
            onFileSelect={handleFileSelect}
            accept="image/*,.pdf,.doc,.docx,.txt"
            maxSize={10 * 1024 * 1024} // 10MB
            multiple
          >
            <Button
              variant="ghost"
              size="icon"
              disabled={disabled}
              aria-label={t('chat.attachFile')}
              title={t('chat.attachFile')}
            >
              <Paperclip className="h-5 w-5" />
            </Button>
          </FileUpload>
        )}

        {/* Text input */}
        <div className="flex-1 relative">
          <Textarea
            ref={textareaRef}
            value={message}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={placeholder}
            maxLength={maxLength}
            rows={1}
            className={cn(
              'min-h-[44px] max-h-[200px] resize-none',
              'pr-20', // Space for character count
              {
                'border-warning': isNearLimit,
              }
            )}
            aria-label={t('chat.messageInput')}
            aria-describedby="character-count"
            aria-invalid={isNearLimit}
          />
          
          {/* Character count */}
          <div
            id="character-count"
            className={cn(
              'absolute right-3 bottom-2 text-xs',
              {
                'text-muted-foreground': !isNearLimit,
                'text-warning': isNearLimit,
                'text-error': characterCount >= maxLength,
              }
            )}
            aria-live="polite"
          >
            {characterCount}/{maxLength}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {/* Emoji picker */}
          <div className="relative">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setShowEmojiPicker(prev => !prev)}
              disabled={disabled}
              aria-label={t('chat.emojiPicker')}
              title={`${t('chat.emojiPicker')} (Ctrl+Shift+E)`}
            >
              <Smile className="h-5 w-5" />
            </Button>
            
            {showEmojiPicker && (
              <div className="absolute bottom-full right-0 mb-2 z-50">
                <EmojiPicker
                  onEmojiSelect={handleEmojiSelect}
                  onClose={() => setShowEmojiPicker(false)}
                />
              </div>
            )}
          </div>

          {/* Voice recording */}
          <VoiceRecorder
            isRecording={isRecording}
            onStartRecording={() => setIsRecording(true)}
            onStopRecording={(blob) => {
              setIsRecording(false);
              handleVoiceRecording(blob);
            }}
            disabled={disabled}
          >
            <Button
              variant="ghost"
              size="icon"
              disabled={disabled}
              aria-label={isRecording ? t('chat.stopRecording') : t('chat.startRecording')}
              title={isRecording ? t('chat.stopRecording') : t('chat.startRecording')}
            >
              {isRecording ? (
                <MicOff className="h-5 w-5 text-error animate-pulse" />
              ) : (
                <Mic className="h-5 w-5" />
              )}
            </Button>
          </VoiceRecorder>

          {/* Send button */}
          <Button
            onClick={handleSend}
            disabled={disabled || !message.trim()}
            size="icon"
            className="bg-primary text-primary-foreground hover:bg-primary/90"
            aria-label={t('chat.sendMessage')}
            title={`${t('chat.sendMessage')} (${enterToSend ? 'Enter' : 'Ctrl+Enter'})`}
          >
            <Send className="h-5 w-5" />
          </Button>
        </div>
      </div>

      {/* Typing indicator placeholder */}
      <div className="h-6" aria-live="polite" aria-atomic="true">
        {/* Typing indicator will be rendered here */}
      </div>

      {/* Accessibility shortcuts info */}
      <div className="sr-only" role="status" aria-live="polite">
        {showEmojiPicker && t('chat.emojiPickerOpen')}
        {showFileUpload && t('chat.fileUploadOpen')}
        {isRecording && t('chat.recordingInProgress')}
      </div>
    </div>
  );
};

export default MessageInput;
```

## frontend/src/components/Chat/TypingIndicator.tsx
```typescript
import React, { useState, useEffect } from 'react';
import { cn } from '@utils/cn';
import { useTranslation } from 'react-i18next';

interface TypingIndicatorProps {
  users: string[];
  className?: string;
  timeout?: number;
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  users,
  className = '',
  timeout = 3000,
}) => {
  const { t } = useTranslation();
  const [displayText, setDisplayText] = useState('');
  const [animationPhase, setAnimationPhase] = useState(0);

  // Generate typing text based on user count
  useEffect(() => {
    if (users.length === 0) {
      setDisplayText('');
      return;
    }

    let text = '';
    if (users.length === 1) {
      text = t('chat.typing.single', { user: users[0] });
    } else if (users.length === 2) {
      text = t('chat.typing.double', { user1: users[0], user2: users[1] });
    } else {
      text = t('chat.typing.multiple', { count: users.length });
    }

    setDisplayText(text);
  }, [users, t]);

  // Animate dots
  useEffect(() => {
    if (!displayText) return;

    const interval = setInterval(() => {
      setAnimationPhase(prev => (prev + 1) % 4);
    }, 500);

    return () => clearInterval(interval);
  }, [displayText]);

  // Clear typing indicator after timeout
  useEffect(() => {
    if (users.length === 0) return;

    const timer = setTimeout(() => {
      // Typing should be cleared by the WebSocket service
    }, timeout);

    return () => clearTimeout(timer);
  }, [users, timeout]);

  if (!displayText) return null;

  const dots = ['.', '..', '...', ''][animationPhase];

  return (
    <div
      className={cn(
        'flex items-center gap-2 px-3 py-2',
        'bg-muted/80 rounded-lg',
        'text-sm text-muted-foreground',
        'animate-pulse',
        className
      )}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      {/* Typing animation dots */}
      <div className="flex items-center gap-1" aria-hidden="true">
        <span
          className={cn(
            'w-2 h-2 bg-current rounded-full',
            'animate-bounce',
            { 'animation-delay-100': animationPhase === 1 }
          )}
        />
        <span
          className={cn(
            'w-2 h-2 bg-current rounded-full',
            'animate-bounce',
            { 'animation-delay-200': animationPhase === 2 }
          )}
        />
        <span
          className={cn(
            'w-2 h-2 bg-current rounded-full',
            'animate-bounce',
            { 'animation-delay-300': animationPhase === 3 }
          )}
        />
      </div>

      {/* Typing text */}
      <span className="flex-1">
        {displayText}
        <span aria-hidden="true">{dots}</span>
      </span>

      {/* Screen reader only text */}
      <span className="sr-only">
        {t('chat.typing.srOnly', { count: users.length })}
      </span>
    </div>
  );
};

export default TypingIndicator;
```

## frontend/src/components/Chat/ChatHeader.tsx
```typescript
import React, { useState } from 'react';
import { MoreVertical, Phone, Video, UserPlus, Flag, Info } from 'lucide-react';
import { Button } from '@components/UI/Button';
import { Badge } from '@components/UI/Badge';
import { DropdownMenu } from '@components/UI/DropdownMenu';
import { Avatar } from '@components/UI/Avatar';
import { cn } from '@utils/cn';
import { useTranslation } from 'react-i18next';
import { useAppSelector } from '@store/hooks';
import type { Conversation } from '@store/types';

interface ChatHeaderProps {
  conversation: Conversation | null;
  isConnected: boolean;
  onQuickAction: (action: string, data?: Record<string, unknown>) => void;
  className?: string;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  conversation,
  isConnected,
  onQuickAction,
  className = '',
}) => {
  const { t } = useTranslation();
  const [showDetails, setShowDetails] = useState(false);

  if (!conversation) {
    return (
      <div className={cn('p-4 border-b border-border', className)}>
        <div className="flex items-center justify-between">
          <div className="text-muted-foreground">
            {t('chat.noConversation')}
          </div>
          <div className="flex items-center gap-2">
            <ConnectionStatus isConnected={isConnected} />
          </div>
        </div>
      </div>
    );
  }

  const quickActions = [
    {
      label: t('chat.header.escalate'),
      action: 'escalate',
      icon: Flag,
      variant: 'destructive' as const,
      visible: !conversation.escalated && conversation.status !== 'resolved',
    },
    {
      label: t('chat.header.resolve'),
      action: 'resolve',
      icon: Flag,
      variant: 'default' as const,
      visible: conversation.status !== 'resolved',
    },
    {
      label: t('chat.header.transfer'),
      action: 'transfer',
      icon: UserPlus,
      variant: 'outline' as const,
      visible: conversation.status === 'active',
    },
  ].filter(action => action.visible);

  const handleAction = (action: string) => {
    switch (action) {
      case 'escalate':
        onQuickAction('escalate', { reason: 'User requested escalation' });
        break;
      case 'resolve':
        onQuickAction('resolve', {});
        break;
      case 'transfer':
        onQuickAction('transfer', {});
        break;
      default:
        console.warn('Unknown action:', action);
    }
  };

  return (
    <div className={cn('p-4 border-b border-border bg-background', className)}>
      <div className="flex items-center justify-between">
        {/* Left side - Conversation info */}
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Avatar/Icon */}
          <div className="relative">
            <Avatar
              src={conversation.metadata?.avatarUrl}
              alt={conversation.title || t('chat.conversation')}
              size="md"
              className="bg-primary/10"
            >
              {conversation.channel?.charAt(0).toUpperCase() || '💬'}
            </Avatar>
            
            {/* Status indicator */}
            <div className={cn(
              'absolute -bottom-1 -right-1 w-3 h-3 rounded-full border-2 border-background',
              {
                'bg-success': conversation.status === 'active',
                'bg-warning': conversation.status === 'waiting_for_agent' || conversation.status === 'waiting_for_user',
                'bg-error': conversation.escalated,
                'bg-muted': conversation.status === 'resolved',
              }
            )} />
          </div>

          {/* Conversation details */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-lg font-semibold truncate">
                {conversation.title || t('chat.conversation')}
              </h2>
              
              {/* Priority badge */}
              {conversation.priority !== 'medium' && (
                <Badge
                  variant={conversation.priority === 'urgent' || conversation.priority === 'critical' ? 'destructive' : 'default'}
                  size="sm"
                >
                  {t(`chat.priority.${conversation.priority}`)}
                </Badge>
              )}
              
              {/* Status badge */}
              <Badge
                variant={conversation.status === 'resolved' ? 'success' : 'secondary'}
                size="sm"
              >
                {t(`chat.status.${conversation.status}`)}
              </Badge>
              
              {/* Escalated indicator */}
              {conversation.escalated && (
                <Badge variant="destructive" size="sm">
                  {t('chat.escalated')}
                </Badge>
              )}
            </div>
            
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>{t(`chat.channel.${conversation.channel}`)}</span>
              <span>•</span>
              <span>{t('chat.messages', { count: conversation.messageCount })}</span>
              {conversation.assignedAgentId && (
                <>
                  <span>•</span>
                  <span>{t('chat.assignedTo', { agent: conversation.assignedAgentId })}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Right side - Actions and status */}
        <div className="flex items-center gap-2">
          {/* Connection status */}
          <ConnectionStatus isConnected={isConnected} />

          {/* Quick actions */}
          <div className="hidden sm:flex items-center gap-1">
            {quickActions.map((action) => (
              <Button
                key={action.action}
                variant={action.variant}
                size="sm"
                onClick={() => handleAction(action.action)}
                title={action.label}
                aria-label={action.label}
              >
                <action.icon className="h-4 w-4 mr-1" />
                <span className="hidden md:inline">{action.label}</span>
              </Button>
            ))}
          </div>

          {/* More actions menu */}
          <DropdownMenu>
            <DropdownMenu.Trigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label={t('chat.moreActions')}
                title={t('chat.moreActions')}
              >
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenu.Trigger>
            
            <DropdownMenu.Content align="end" className="w-48">
              <DropdownMenu.Label>{t('chat.actions')}</DropdownMenu.Label>
              
              {quickActions.map((action) => (
                <DropdownMenu.Item
                  key={action.action}
                  onClick={() => handleAction(action.action)}
                  className="flex items-center gap-2"
                >
                  <action.icon className="h-4 w-4" />
                  <span>{action.label}</span>
                </DropdownMenu.Item>
              ))}
              
              <DropdownMenu.Separator />
              
              <DropdownMenu.Item
                onClick={() => setShowDetails(true)}
                className="flex items-center gap-2"
              >
                <Info className="h-4 w-4" />
                <span>{t('chat.viewDetails')}</span>
              </DropdownMenu.Item>
            </DropdownMenu.Content>
          </DropdownMenu>
        </div>
      </div>

      {/* Sentiment and emotion indicators */}
      {conversation.sentimentCurrent && conversation.emotionCurrent && (
        <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
          <span>{t('chat.sentiment')}: {conversation.sentimentCurrent}</span>
          <span>•</span>
          <span>{t('chat.emotion')}: {conversation.emotionCurrent}</span>
        </div>
      )}
    </div>
  );
};

// Connection status component
const ConnectionStatus: React.FC<{ isConnected: boolean }> = ({ isConnected }) => {
  const { t } = useTranslation();
  
  return (
    <div
      className={cn(
        'flex items-center gap-2 px-2 py-1 rounded-full text-xs',
        {
          'bg-success/10 text-success': isConnected,
          'bg-warning/10 text-warning': !isConnected,
        }
      )}
      role="status"
      aria-live="polite"
    >
      <div
        className={cn(
          'w-2 h-2 rounded-full',
          {
            'bg-success animate-pulse': isConnected,
            'bg-warning': !isConnected,
          }
        )}
        aria-hidden="true"
      />
      <span>{isConnected ? t('chat.connected') : t('chat.disconnected')}</span>
    </div>
  );
};

export default ChatHeader;
```

## frontend/src/components/UI/Button.tsx
```typescript
import React, { forwardRef } from 'react';
import { cn } from '@utils/cn';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',
        success: 'bg-success text-success-foreground hover:bg-success/90',
        warning: 'bg-warning text-warning-foreground hover:bg-warning/90',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3',
        lg: 'h-11 rounded-md px-8',
        icon: 'h-10 w-10',
        'icon-sm': 'h-8 w-8',
        'icon-lg': 'h-12 w-12',
      },
      fullWidth: {
        true: 'w-full',
      },
      loading: {
        true: 'relative',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
  loadingText?: string;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, loading = false, loadingText, fullWidth, children, disabled, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    
    const isDisabled = disabled || loading;
    
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, fullWidth, loading, className }))}
        ref={ref}
        disabled={isDisabled}
        aria-busy={loading}
        aria-disabled={isDisabled}
        {...props}
      >
        {loading && (
          <span className="absolute inset-0 flex items-center justify-center">
            <svg
              className="animate-spin h-4 w-4"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
          </span>
        )}
        
        <span className={cn({ 'opacity-0': loading, 'opacity-100': !loading })}>
          {loading && loadingText ? loadingText : children}
        </span>
      </Comp>
    );
  }
);

Button.displayName = 'Button';

export { Button, buttonVariants };
export type { ButtonProps };
```

## frontend/src/components/UI/Textarea.tsx
```typescript
import React, { forwardRef, useRef, useEffect } from 'react';
import { cn } from '@utils/cn';

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
  helperText?: string;
  label?: string;
  required?: boolean;
}

const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, error, helperText, label, required, id, ...props }, ref) => {
    const textareaId = id || `textarea-${Math.random().toString(36).substr(2, 9)}`;
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Auto-resize functionality
    useEffect(() => {
      const textarea = textareaRef.current;
      if (textarea && props.rows === undefined) {
        const resize = () => {
          textarea.style.height = 'auto';
          textarea.style.height = `${textarea.scrollHeight}px`;
        };
        
        textarea.addEventListener('input', resize);
        resize(); // Initial resize
        
        return () => textarea.removeEventListener('input', resize);
      }
    }, [props.rows]);

    return (
      <div className="w-full space-y-2">
        {label && (
          <label
            htmlFor={textareaId}
            className={cn(
              'text-sm font-medium',
              error ? 'text-destructive' : 'text-foreground'
            )}
          >
            {label}
            {required && <span className="text-destructive ml-1">*</span>}
          </label>
        )}
        
        <div className="relative">
          <textarea
            ref={(node) => {
              textareaRef.current = node;
              if (typeof ref === 'function') ref(node);
              else if (ref) ref.current = node;
            }}
            id={textareaId}
            className={cn(
              'flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2',
              'text-sm ring-offset-background placeholder:text-muted-foreground',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
              'disabled:cursor-not-allowed disabled:opacity-50',
              'resize-none', // Disable manual resize
              error && 'border-destructive focus-visible:ring-destructive',
              className
            )}
            aria-invalid={error}
            aria-describedby={helperText ? `${textareaId}-helper` : undefined}
            {...props}
          />
        </div>
        
        {helperText && (
          <p
            id={`${textareaId}-helper`}
            className={cn(
              'text-sm',
              error ? 'text-destructive' : 'text-muted-foreground'
            )}
          >
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';

export { Textarea };
export type { TextareaProps };
```

## frontend/src/components/Accessibility/AccessibilityProvider.tsx
```typescript
import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useAppSelector } from '@store/hooks';
import type { RootState } from '@store/types';

interface AccessibilityContextType {
  announce: (message: string, priority?: 'polite' | 'assertive') => void;
  focus: (element: HTMLElement | null) => void;
  trapFocus: (container: HTMLElement) => void;
  releaseFocus: () => void;
  skipToMain: () => void;
  highContrast: boolean;
  reducedMotion: boolean;
  screenReaderMode: boolean;
}

const AccessibilityContext = createContext<AccessibilityContextType | undefined>(undefined);

interface AccessibilityProviderProps {
  children: ReactNode;
}

export const AccessibilityProvider: React.FC<AccessibilityProviderProps> = ({ children }) => {
  const { highContrast, reducedMotion, screenReaderAnnouncements } = useAppSelector(
    (state: RootState) => state.ui.accessibility
  );

  const [screenReaderMode, setScreenReaderMode] = useState(false);

  // Detect screen reader usage
  useEffect(() => {
    const detectScreenReader = () => {
      // Check for screen reader indicators
      const indicators = [
        'ontouchstart' in window && navigator.maxTouchPoints === 0, // VoiceOver on iOS
        navigator.userAgent.includes('JAWS'),
        navigator.userAgent.includes('NVDA'),
        navigator.userAgent.includes('VoiceOver'),
      ];

      setScreenReaderMode(indicators.some(Boolean) || screenReaderAnnouncements);
    };

    detectScreenReader();
    
    // Listen for accessibility events
    window.addEventListener('mousemove', detectScreenReader, { once: true });
    window.addEventListener('keydown', detectScreenReader, { once: true });

    return () => {
      window.removeEventListener('mousemove', detectScreenReader);
      window.removeEventListener('keydown', detectScreenReader);
    };
  }, [screenReaderAnnouncements]);

  // Apply accessibility settings
  useEffect(() => {
    const root = document.documentElement;
    
    // High contrast mode
    if (highContrast) {
      root.classList.add('high-contrast');
    } else {
      root.classList.remove('high-contrast');
    }
    
    // Reduced motion
    if (reducedMotion) {
      root.style.setProperty('--animation-duration', '0.01ms');
      root.style.setProperty('--transition-duration', '0.01ms');
    } else {
      root.style.removeProperty('--animation-duration');
      root.style.removeProperty('--transition-duration');
    }
  }, [highContrast, reducedMotion]);

  // Announce messages to screen readers
  const announce = (message: string, priority: 'polite' | 'assertive' = 'polite') => {
    if (!screenReaderMode) return;

    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', priority);
    announcement.className = 'sr-only';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    
    // Remove after announcement
    setTimeout(() => {
      document.body.removeChild(announcement);
    }, 1000);
  };

  // Focus management
  const focus = (element: HTMLElement | null) => {
    if (element) {
      element.focus();
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      
      // Announce focus change
      if (element.getAttribute('aria-label')) {
        announce(`Focused on ${element.getAttribute('aria-label')}`, 'polite');
      }
    }
  };

  // Focus trap for modals
  const trapFocus = (container: HTMLElement) => {
    const focusableElements = container.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return;
      
      if (event.shiftKey) {
        if (document.activeElement === firstElement) {
          lastElement.focus();
          event.preventDefault();
        }
      } else {
        if (document.activeElement === lastElement) {
          firstElement.focus();
          event.preventDefault();
        }
      }
    };
    
    container.addEventListener('keydown', handleKeyDown);
    
    // Focus first element
    if (firstElement) {
      firstElement.focus();
    }
    
    // Return cleanup function
    return () => {
      container.removeEventListener('keydown', handleKeyDown);
    };
  };

  // Release focus trap
  const releaseFocus = () => {
    // Remove any active focus traps
    document.querySelectorAll('[data-focus-trap]').forEach(element => {
      element.removeAttribute('data-focus-trap');
    });
  };

  // Skip to main content
  const skipToMain = () => {
    const mainContent = document.getElementById('main-content');
    if (mainContent) {
      focus(mainContent);
      announce('Skipped to main content', 'assertive');
    }
  };

  // Keyboard navigation enhancement
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Skip link (Alt + S)
      if (event.altKey && event.key === 's') {
        event.preventDefault();
        skipToMain();
      }
      
      // High contrast toggle (Alt + H)
      if (event.altKey && event.key === 'h') {
        event.preventDefault();
        // Dispatch high contrast toggle
        window.dispatchEvent(new CustomEvent('toggle-high-contrast'));
      }
      
      // Reduced motion toggle (Alt + M)
      if (event.altKey && event.key === 'm') {
        event.preventDefault();
        // Dispatch reduced motion toggle
        window.dispatchEvent(new CustomEvent('toggle-reduced-motion'));
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Focus visible enhancement
  useEffect(() => {
    const handleFocus = (event: FocusEvent) => {
      const target = event.target as HTMLElement;
      if (target) {
        target.setAttribute('data-focus-visible', 'true');
      }
    };

    const handleBlur = (event: FocusEvent) => {
      const target = event.target as HTMLElement;
      if (target) {
        target.removeAttribute('data-focus-visible');
      }
    };

    document.addEventListener('focus', handleFocus, true);
    document.addEventListener('blur', handleBlur, true);

    return () => {
      document.removeEventListener('focus', handleFocus, true);
      document.removeEventListener('blur', handleBlur, true);
    };
  }, []);

  // Announce page changes
  useEffect(() => {
    const handleRouteChange = () => {
      const pageTitle = document.title;
      announce(`Navigated to ${pageTitle}`, 'polite');
    };

    window.addEventListener('route-change', handleRouteChange);
    return () => window.removeEventListener('route-change', handleRouteChange);
  }, []);

  const value: AccessibilityContextType = {
    announce,
    focus,
    trapFocus,
    releaseFocus,
    skipToMain,
    highContrast,
    reducedMotion,
    screenReaderMode,
  };

  return (
    <AccessibilityContext.Provider value={value}>
      {/* Skip link */}
      <a
        href="#main-content"
        className="skip-link"
        onClick={(e) => {
          e.preventDefault();
          skipToMain();
        }}
      >
        Skip to main content
      </a>
      
      {/* Live region for announcements */}
      <div
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      />
      
      {/* Live region for assertive announcements */}
      <div
        aria-live="assertive"
        aria-atomic="true"
        className="sr-only"
      />
      
      {children}
    </AccessibilityContext.Provider>
  );
};

// Custom hook for using accessibility context
export const useAccessibility = (): AccessibilityContextType => {
  const context = useContext(AccessibilityContext);
  if (context === undefined) {
    throw new Error('useAccessibility must be used within an AccessibilityProvider');
  }
  return context;
};

// Announcement hook for simple announcements
export const useAnnouncer = () => {
  const { announce } = useAccessibility();
  return announce;
};

export default AccessibilityProvider;
```

## frontend/src/utils/cn.ts
```typescript
import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Utility function to merge Tailwind CSS classes
 * Handles conflicts and merges classes intelligently
 * 
 * @param inputs - Array of class values to merge
 * @returns Merged class string
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Conditional class utility
 * 
 * @param conditions - Object with class names as keys and boolean conditions as values
 * @returns String of classes where conditions are true
 */
export function conditionalClasses(conditions: Record<string, boolean>): string {
  return Object.entries(conditions)
    .filter(([, condition]) => Boolean(condition))
    .map(([className]) => className)
    .join(' ');
}

/**
 * Variant class utility for component variants
 * 
 * @param base - Base classes
 * @param variants - Object with variant names and their class strings
 * @param activeVariant - Current active variant
 * @returns Merged class string
 */
export function variantClasses(
  base: string,
  variants: Record<string, string>,
  activeVariant?: string
): string {
  return cn(base, activeVariant ? variants[activeVariant] : '');
}

/**
 * Responsive class utility
 * 
 * @param screens - Object with screen sizes and their classes
 * @returns String with responsive classes
 */
export function responsiveClasses(screens: Record<string, string>): string {
  return Object.entries(screens)
    .map(([screen, classes]) => {
      if (screen === 'default') return classes;
      return `${screen}:${classes}`;
    })
    .join(' ');
}

/**
 * State class utility for component states
 * 
 * @param base - Base classes
 * @param states - Object with state names and their class strings
 * @param activeStates - Array of active state names
 * @returns Merged class string
 */
export function stateClasses(
  base: string,
  states: Record<string, string>,
  activeStates: string[] = []
): string {
  const stateClasses = activeStates.map(state => states[state]).join(' ');
  return cn(base, stateClasses);
}

/**
 * Animation class utility with reduced motion support
 * 
 * @param animation - Animation class string
 * @param reducedMotionFallback - Fallback class for reduced motion
 * @returns Appropriate class string based on user preferences
 */
export function animationClasses(
  animation: string,
  reducedMotionFallback = ''
): string {
  // Check if user prefers reduced motion
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  
  if (prefersReducedMotion && reducedMotionFallback) {
    return reducedMotionFallback;
  }
  
  return animation;
}

/**
 * Focus ring classes with high contrast support
 * 
 * @param color - Focus ring color (default: primary)
 * @returns Focus ring classes
 */
export function focusRingClasses(color: string = 'primary'): string {
  return cn(
    'focus-visible:outline-none',
    'focus-visible:ring-2',
    `focus-visible:ring-${color}`,
    'focus-visible:ring-offset-2',
    'focus-visible:ring-offset-background'
  );
}

/**
 * High contrast mode classes
 * 
 * @param normal - Normal mode classes
 * @param highContrast - High contrast mode classes
 * @returns Appropriate classes based on user preferences
 */
export function highContrastClasses(
  normal: string,
  highContrast: string
): string {
  // This would need to check for high contrast preference
  // For now, return normal classes
  return normal;
}

/**
 * Utility to merge multiple class objects
 * 
 * @param objects - Array of class objects to merge
 * @returns Merged class object
 */
export function mergeClassObjects<T extends Record<string, any>>(
  ...objects: T[]
): T {
  return objects.reduce((merged, obj) => ({ ...merged, ...obj }), {} as T);
}

// Default export
export { cn as default };
```

## frontend/src/utils/messageUtils.ts
```typescript
import { format, isToday, isYesterday, differenceInMinutes } from 'date-fns';
import { enUS, es } from 'date-fns/locale';
import { Message } from '@store/types';

// Available locales
const LOCALES = { en: enUS, es } as const;
type Locale = keyof typeof LOCALES;

/**
 * Format message timestamp
 */
export const formatMessageTime = (timestamp: string, locale: Locale = 'en'): string => {
  const date = new Date(timestamp);
  const now = new Date();
  
  const diffInMinutes = differenceInMinutes(now, date);
  
  // Less than 1 minute ago
  if (diffInMinutes < 1) {
    return 'just now';
  }
  
  // Less than 1 hour ago
  if (diffInMinutes < 60) {
    return `${diffInMinutes}m ago`;
  }
  
  // Today
  if (isToday(date)) {
    return format(date, 'h:mm a', { locale: LOCALES[locale] });
  }
  
  // Yesterday
  if (isYesterday(date)) {
    return `Yesterday at ${format(date, 'h:mm a', { locale: LOCALES[locale] })}`;
  }
  
  // This week
  if (differenceInMinutes(now, date) < 7 * 24 * 60) {
    return format(date, 'EEEE at h:mm a', { locale: LOCALES[locale] });
  }
  
  // Older
  return format(date, 'MMM d, yyyy at h:mm a', { locale: LOCALES[locale] });
};

/**
 * Format date for date separators
 */
export const formatDateSeparator = (date: Date, locale: Locale = 'en'): string => {
  if (isToday(date)) {
    return 'Today';
  }
  
  if (isYesterday(date)) {
    return 'Yesterday';
  }
  
  if (differenceInMinutes(new Date(), date) < 7 * 24 * 60) {
    return format(date, 'EEEE', { locale: LOCALES[locale] });
  }
  
  return format(date, 'MMMM d, yyyy', { locale: LOCALES[locale] });
};

/**
 * Group messages by date
 */
export const groupMessagesByDate = (messages: Message[]): Record<string, Message[]> => {
  const groups: Record<string, Message[]> = {};
  
  messages.forEach((message) => {
    const messageDate = new Date(message.createdAt);
    const dateKey = format(messageDate, 'yyyy-MM-dd');
    
    if (!groups[dateKey]) {
      groups[dateKey] = [];
    }
    
    groups[dateKey].push(message);
  });
  
  // Convert to readable format
  const readableGroups: Record<string, Message[]> = {};
  Object.entries(groups).forEach(([dateKey, messages]) => {
    const date = new Date(dateKey);
    const readableDate = formatDateSeparator(date);
    readableGroups[readableDate] = messages;
  });
  
  return readableGroups;
};

/**
 * Get icon for message content type
 */
export const getMessageTypeIcon = (contentType: string): string => {
  const iconMap: Record<string, string> = {
    'text': '📝',
    'html': '🌐',
    'markdown': '📄',
    'code': '💻',
    'json': '📊',
    'image': '🖼️',
    'audio': '🎵',
    'video': '🎬',
    'file': '📎',
    'card': '🃏',
    'carousel': '🎠',
    'quick_reply': '⚡',
    'form': '📝',
  };
  
  return iconMap[contentType] || '📝';
};

/**
 * Sanitize message content for display
 */
export const sanitizeMessageContent = (content: string): string => {
  // Basic XSS protection
  return content
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;');
};

/**
 * Get sentiment emoji
 */
export const getSentimentEmoji = (sentiment: string): string => {
  const emojiMap: Record<string, string> = {
    'very_positive': '😊',
    'positive': '🙂',
    'neutral': '😐',
    'negative': '😕',
    'very_negative': '😞',
  };
  
  return emojiMap[sentiment] || '😐';
};

/**
 * Get emotion emoji
 */
export const getEmotionEmoji = (emotion: string): string => {
  const emojiMap: Record<string, string> = {
    'angry': '😠',
    'frustrated': '😤',
    'confused': '😕',
    'neutral': '😐',
    'satisfied': '😌',
    'happy': '😊',
    'excited': '🤗',
  };
  
  return emojiMap[emotion] || '😐';
};

/**
 * Check if message should show timestamp
 */
export const shouldShowTimestamp = (currentMessage: Message, previousMessage?: Message): boolean => {
  if (!previousMessage) return true;
  
  const currentTime = new Date(currentMessage.createdAt).getTime();
  const previousTime = new Date(previousMessage.createdAt).getTime();
  const timeDiff = currentTime - previousTime;
  
  // Show timestamp if more than 1 minute apart
  return timeDiff > 60000;
};

/**
 * Check if messages are from the same sender
 */
export const isSameSender = (message1: Message, message2: Message): boolean => {
  return message1.senderId === message2.senderId;
};

/**
 * Check if messages are consecutive
 */
export const isConsecutiveMessage = (currentMessage: Message, previousMessage?: Message): boolean => {
  if (!previousMessage) return false;
  
  return (
    isSameSender(currentMessage, previousMessage) &&
    !shouldShowTimestamp(currentMessage, previousMessage)
  );
};

/**
 * Extract text content from HTML
 */
export const extractTextFromHTML = (html: string): string => {
  const div = document.createElement('div');
  div.innerHTML = html;
  return div.textContent || div.innerText || '';
};

/**
 * Truncate message content
 */
export const truncateMessage = (content: string, maxLength: number = 100): string => {
  if (content.length <= maxLength) return content;
  
  return content.substring(0, maxLength) + '...';
};

/**
 * Check if message contains profanity
 */
export const containsProfanity = (content: string): boolean => {
  // Basic profanity filter - in production, use a more sophisticated library
  const profanityWords = [
    'damn', 'hell', 'crap', 'stupid', 'idiot',
    // Add more words as needed
  ];
  
  const lowerContent = content.toLowerCase();
  return profanityWords.some(word => lowerContent.includes(word));
};

/**
 * Filter profanity from message
 */
export const filterProfanity = (content: string): string => {
  // Basic profanity filtering
  const profanityMap: Record<string, string> = {
    'damn': 'd***',
    'hell': 'h***',
    'crap': 'c***',
    'stupid': 's*****',
    'idiot': 'i****',
  };
  
  let filteredContent = content;
  Object.entries(profanityMap).forEach(([word, replacement]) => {
    const regex = new RegExp(word, 'gi');
    filteredContent = filteredContent.replace(regex, replacement);
  });
  
  return filteredContent;
};

/**
 * Generate message summary
 */
export const generateMessageSummary = (messages: Message[]): string => {
  if (messages.length === 0) return 'No messages';
  if (messages.length === 1) return '1 message';
  
  const lastMessage = messages[messages.length - 1];
  const sender = lastMessage.senderName || 'Unknown';
  const preview = truncateMessage(extractTextFromHTML(lastMessage.content), 50);
  
  return `${messages.length} messages • Last: ${sender}: ${preview}`;
};

/**
 * Calculate message statistics
 */
export const calculateMessageStats = (messages: Message[]): {
  total: number;
  bySender: Record<string, number>;
  byContentType: Record<string, number>;
  averageLength: number;
} => {
  const stats = {
    total: messages.length,
    bySender: {} as Record<string, number>,
    byContentType: {} as Record<string, number>,
    averageLength: 0,
  };

  let totalLength = 0;

  messages.forEach((message) => {
    // Count by sender
    const sender = message.senderName || 'Unknown';
    stats.bySender[sender] = (stats.bySender[sender] || 0) + 1;

    // Count by content type
    const contentType = message.contentType || 'text';
    stats.byContentType[contentType] = (stats.byContentType[contentType] || 0) + 1;

    // Calculate total length
    totalLength += message.content.length;
  });

  stats.averageLength = stats.total > 0 ? totalLength / stats.total : 0;

  return stats;
};
```

Now let me create some essential test files and configuration:

## frontend/src/components/Chat/__tests__/ChatWindow.test.tsx
```typescript
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatWindow } from '../ChatWindow';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';
import { authSlice } from '@store/slices/authSlice';
import { conversationSlice } from '@store/slices/conversationSlice';
import { uiSlice } from '@store/slices/uiSlice';
import { websocketSlice } from '@store/slices/websocketSlice';

// Mock hooks
jest.mock('@hooks/useAuth', () => ({
  useAuth: () => ({
    isAuthenticated: true,
    isLoading: false,
    user: { id: 'user123', displayName: 'Test User' },
  }),
}));

jest.mock('@hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    isConnected: true,
  }),
}));

jest.mock('@hooks/useConversation', () => ({
  useConversation: () => ({
    currentConversation: {
      id: 'conv123',
      title: 'Test Conversation',
      status: 'active',
      channel: 'web_chat',
      priority: 'medium',
      messageCount: 5,
      messages: [
        {
          id: 'msg1',
          content: 'Hello',
          senderType: 'user',
          senderId: 'user123',
          createdAt: new Date().toISOString(),
        },
        {
          id: 'msg2',
          content: 'Hi there!',
          senderType: 'ai_agent',
          senderId: 'ai123',
          createdAt: new Date().toISOString(),
        },
      ],
    },
    sendMessage: jest.fn(),
  }),
}));

// Mock services
jest.mock('@services/websocket/websocketService', () => ({
  websocketService: {
    send: jest.fn(),
  },
}));

// Create test store
const createTestStore = () => {
  return configureStore({
    reducer: {
      auth: authSlice.reducer,
      conversation: conversationSlice.reducer,
      ui: uiSlice.reducer,
      websocket: websocketSlice.reducer,
    },
    preloadedState: {
      auth: {
        isAuthenticated: true,
        user: { id: 'user123', displayName: 'Test User' },
        token: 'test-token',
      },
      conversation: {
        conversations: [],
        currentConversation: null,
        messages: [],
        isLoading: false,
        error: null,
      },
      ui: {
        theme: 'light',
        language: 'en',
        fontSize: 'medium',
        reducedMotion: false,
        highContrast: false,
        chat: {
          autoScroll: true,
          showTimestamps: true,
          showAvatars: true,
          compactMode: false,
          enterToSend: true,
        },
      },
      websocket: {
        isConnected: true,
        connectionId: 'conn123',
      },
    },
  });
};

describe('ChatWindow', () => {
  let store: ReturnType<typeof createTestStore>;
  let mockSendMessage: jest.Mock;

  beforeEach(() => {
    store = createTestStore();
    mockSendMessage = jest.fn();
    jest.clearAllMocks();
  });

  const renderChatWindow = (conversationId = 'conv123') => {
    return render(
      <Provider store={store}>
        <BrowserRouter>
          <ChatWindow />
        </BrowserRouter>
      </Provider>
    );
  };

  test('renders chat window with conversation', () => {
    renderChatWindow();

    // Check if conversation title is displayed
    expect(screen.getByText('Test Conversation')).toBeInTheDocument();
    
    // Check if messages are rendered
    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('Hi there!')).toBeInTheDocument();
    
    // Check if input is present
    expect(screen.getByRole('textbox', { name: /message input/i })).toBeInTheDocument();
  });

  test('sends message when Enter is pressed (enterToSend=true)', async () => {
    const user = userEvent.setup();
    renderChatWindow();

    const input = screen.getByRole('textbox', { name: /message input/i });
    
    await user.type(input, 'Test message');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(mockSendMessage).toHaveBeenCalledWith('Test message', 'text');
    });
  });

  test('does not send message on Enter when enterToSend=false', async () => {
    const user = userEvent.setup();
    
    // Update store to set enterToSend to false
    store.dispatch(uiSlice.actions.updateChatSettings({ enterToSend: false }));
    
    renderChatWindow();

    const input = screen.getByRole('textbox', { name: /message input/i });
    
    await user.type(input, 'Test message');
    await user.keyboard('{Enter}');

    expect(mockSendMessage).not.toHaveBeenCalled();
  });

  test('sends message with Ctrl+Enter when enterToSend=false', async () => {
    const user = userEvent.setup();
    
    // Update store to set enterToSend to false
    store.dispatch(uiSlice.actions.updateChatSettings({ enterToSend: false }));
    
    renderChatWindow();

    const input = screen.getByRole('textbox', { name: /message input/i });
    
    await user.type(input, 'Test message');
    await user.keyboard('{Control>}{Enter}{/Control}');

    await waitFor(() => {
      expect(mockSendMessage).toHaveBeenCalledWith('Test message', 'text');
    });
  });

  test('shows typing indicator when users are typing', () => {
    renderChatWindow();

    // Simulate typing indicator
    window.dispatchEvent(new CustomEvent('typing-indicator', {
      detail: {
        conversationId: 'conv123',
        userId: 'ai123',
        userName: 'AI Assistant',
        isTyping: true,
      },
    }));

    expect(screen.getByText(/AI Assistant is typing/i)).toBeInTheDocument();
  });

  test('handles file upload', async () => {
    const user = userEvent.setup();
    const mockFileUpload = jest.fn();
    
    render(
      <Provider store={store}>
        <BrowserRouter>
          <ChatWindow onFileUpload={mockFileUpload} />
        </BrowserRouter>
      </Provider>
    );

    const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
    const input = screen.getByLabelText(/attach file/i);
    
    await user.upload(input, file);

    await waitFor(() => {
      expect(mockFileUpload).toHaveBeenCalledWith(file);
    });
  });

  test('shows connection status', () => {
    renderChatWindow();

    expect(screen.getByText('Connected')).toBeInTheDocument();
  });

  test('shows disconnected status when not connected', () => {
    // Mock disconnected state
    jest.mock('@hooks/useWebSocket', () => ({
      useWebSocket: () => ({
        isConnected: false,
      }),
    }));

    renderChatWindow();

    expect(screen.getByText('Disconnected')).toBeInTheDocument();
  });

  test('handles keyboard shortcuts', async () => {
    const user = userEvent.setup();
    renderChatWindow();

    const input = screen.getByRole('textbox', { name: /message input/i });
    
    // Focus input
    await user.click(input);
    
    // Test emoji picker shortcut
    await user.keyboard('{Control>}{Shift>}E{/Shift}{/Control}');
    
    // Emoji picker should be visible
    expect(screen.getByText(/emoji picker/i)).toBeInTheDocument();
  });

  test('respects reduced motion preference', () => {
    // Set reduced motion
    store.dispatch(uiSlice.actions.setReducedMotion(true));
    
    renderChatWindow();

    const container = screen.getByRole('log');
    expect(container).toHaveAttribute('data-reduced-motion', 'true');
  });

  test('announces new messages to screen readers', async () => {
    const user = userEvent.setup();
    renderChatWindow();

    const input = screen.getByRole('textbox', { name: /message input/i });
    
    await user.type(input, 'New message');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      // Check if announcement was made
      const announcer = screen.getByRole('status', { hidden: true });
      expect(announcer).toHaveTextContent(/message sent/i);
    });
  });

  test('handles errors gracefully', async () => {
    // Mock error state
    const errorMessage = 'Failed to send message';
    mockSendMessage.mockRejectedValueOnce(new Error(errorMessage));
    
    const user = userEvent.setup();
    renderChatWindow();

    const input = screen.getByRole('textbox', { name: /message input/i });
    
    await user.type(input, 'Test message');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });

  test('meets accessibility standards', async () => {
    const { container } = renderChatWindow();

    // Check for proper ARIA labels
    expect(screen.getByRole('log')).toHaveAttribute('aria-label', /message list/i);
    expect(screen.getByRole('textbox', { name: /message input/i })).toBeInTheDocument();
    
    // Check for skip links
    expect(screen.getByText(/skip to main content/i)).toBeInTheDocument();
    
    // Check for proper heading structure
    const headings = container.querySelectorAll('h1, h2, h3, h4, h5, h6');
    expect(headings.length).toBeGreaterThan(0);
  });
});
```

## frontend/src/vitest.config.ts
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.ts',
        '**/mockData.ts',
        '**/__mocks__/**',
      ],
      thresholds: {
        lines: 85,
        functions: 85,
        branches: 85,
        statements: 85,
      },
    },
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@services': path.resolve(__dirname, './src/services'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@store': path.resolve(__dirname, './src/store'),
      '@utils': path.resolve(__dirname, './src/utils'),
      '@types': path.resolve(__dirname, './src/types'),
      '@assets': path.resolve(__dirname, './src/assets'),
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@services': path.resolve(__dirname, './src/services'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@store': path.resolve(__dirname, './src/store'),
      '@utils': path.resolve(__dirname, './src/utils'),
      '@types': path.resolve(__dirname, './src/types'),
      '@assets': path.resolve(__dirname, './src/assets'),
    },
  },
});
```

## frontend/src/test/setup.ts
```typescript
import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Mock WebSocket
class MockWebSocket {
  constructor(url: string) {
    this.url = url;
    this.readyState = WebSocket.CONNECTING;
    setTimeout(() => {
      this.onopen?.(new Event('open'));
      this.readyState = WebSocket.OPEN;
    }, 0);
  }
  
  url: string;
  readyState: number;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  
  send(data: string) {
    // Mock implementation
  }
  
  close(code?: number, reason?: string) {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close'));
  }
}

global.WebSocket = MockWebSocket as any;

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};

global.localStorage = localStorageMock as any;

// Mock sessionStorage
const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};

global.sessionStorage = sessionStorageMock as any;

// Mock Notification API
global.Notification = vi.fn().mockImplementation(() => ({
  close: vi.fn(),
}));

// Mock geolocation
global.navigator.geolocation = {
  getCurrentPosition: vi.fn(),
  watchPosition: vi.fn(),
  clearWatch: vi.fn(),
};

// Mock media devices
global.navigator.mediaDevices = {
  getUserMedia: vi.fn().mockResolvedValue({
    getTracks: () => [],
  }),
  enumerateDevices: vi.fn().mockResolvedValue([]),
};

// Accessibility test utilities
export const testAccessibility = async (container: HTMLElement) => {
  // Check for proper ARIA labels
  const elementsWithoutLabels = container.querySelectorAll(
    'button:not([aria-label]):not([aria-labelledby]):not([title]), ' +
    'input:not([aria-label]):not([aria-labelledby]):not([id]), ' +
    'textarea:not([aria-label]):not([aria-labelledby]):not([id]), ' +
    'select:not([aria-label]):not([aria-labelledby]):not([id])'
  );
  
  if (elementsWithoutLabels.length > 0) {
    console.warn('Elements missing accessibility labels:', elementsWithoutLabels);
  }

  // Check for focus management
  const focusableElements = container.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  
  // Check for proper heading structure
  const headings = container.querySelectorAll('h1, h2, h3, h4, h5, h6');
  const headingLevels = Array.from(headings).map(h => parseInt(h.tagName.charAt(1)));
  
  // Check for skip links
  const skipLinks = container.querySelectorAll('.skip-link');
  
  // Check for color contrast (basic check)
  const elementsWithPoorContrast = container.querySelectorAll(
    '[style*="color"]:not([style*="background"])'
  );

  return {
    hasAccessibilityLabels: elementsWithoutLabels.length === 0,
    focusableElementsCount: focusableElements.length,
    headingStructure: headingLevels,
    hasSkipLinks: skipLinks.length > 0,
    elementsWithPoorContrast: elementsWithPoorContrast.length,
  };
};

// Custom matchers for accessibility
expect.extend({
  toHaveAccessibleLabel(received: HTMLElement, expected?: string) {
    const label = received.getAttribute('aria-label') || 
                  received.getAttribute('aria-labelledby') ||
                  received.getAttribute('title');
    
    if (expected) {
      return {
        pass: label === expected,
        message: () => `Expected element to have aria-label "${expected}", but got "${label}"`,
      };
    }
    
    return {
      pass: !!label,
      message: () => 'Expected element to have an accessible label',
    };
  },
  
  toBeFocusable(received: HTMLElement) {
    const isFocusable = received.matches('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    
    return {
      pass: isFocusable,
      message: () => 'Expected element to be focusable',
    };
  },
  
  toHaveValidHeadingStructure(received: HTMLElement[]) {
    const headingLevels = received.map(h => parseInt(h.tagName.charAt(1)));
    const isValid = headingLevels.every((level, index) => {
      if (index === 0) return true;
      return level <= headingLevels[index - 1] + 1;
    });
    
    return {
      pass: isValid,
      message: () => 'Expected valid heading structure (no skipping levels)',
    };
  },
});

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: {
      language: 'en',
      changeLanguage: vi.fn(),
    },
  }),
  Trans: ({ children }: { children: ReactNode }) => children,
}));

// Mock React Router
vi.mock('react-router-dom', () => ({
  ...vi.importActual('react-router-dom'),
  useParams: () => ({ conversationId: 'conv123' }),
  useNavigate: () => vi.fn(),
  useLocation: () => ({ pathname: '/chat/conv123' }),
}));

// Global test utilities
export const createMockStore = (initialState: any) => {
  return configureStore({
    reducer: {
      auth: authSlice.reducer,
      conversation: conversationSlice.reducer,
      ui: uiSlice.reducer,
      websocket: websocketSlice.reducer,
    },
    preloadedState: initialState,
  });
};

export const renderWithProviders = (
  ui: React.ReactElement,
  { 
    store = createMockStore({}),
    ...renderOptions 
  } = {}
) => {
  function Wrapper({ children }: { children: React.ReactElement }) {
    return (
      <Provider store={store}>
        <BrowserRouter>
          <AccessibilityProvider>
            {children}
          </AccessibilityProvider>
        </BrowserRouter>
      </Provider>
    );
  }
  
  return render(ui, { wrapper: Wrapper, ...renderOptions });
};

// Performance monitoring
export const measurePerformance = async (callback: () => Promise<void>) => {
  const start = performance.now();
  await callback();
  const end = performance.now();
  return end - start;
};

// Mock data generators
export const generateMockMessage = (overrides?: Partial<Message>): Message => ({
  id: `msg_${Math.random().toString(36).substr(2, 9)}`,
  conversationId: 'conv123',
  organizationId: 'org123',
  senderType: 'user',
  senderId: 'user123',
  senderName: 'Test User',
  content: 'Test message',
  contentType: 'text',
  createdAt: new Date().toISOString(),
  aiProcessed: false,
  isFlagged: false,
  isEdited: false,
  hasAttachments: false,
  attachments: [],
  metadata: {},
  ...overrides,
});

export const generateMockConversation = (overrides?: Partial<Conversation>): Conversation => ({
  id: 'conv123',
  organizationId: 'org123',
  userId: 'user123',
  conversationNumber: 1,
  title: 'Test Conversation',
  channel: 'web_chat',
  status: 'active',
  priority: 'medium',
  isUrgent: false,
  startedAt: new Date().toISOString(),
  lastActivityAt: new Date().toISOString(),
  messageCount: 2,
  aiHandled: true,
  resolved: false,
  escalated: false,
  language: 'en',
  tags: [],
  metadata: {},
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  ...overrides,
});
```

## frontend/.env.example
```env
# API Configuration
VITE_API_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/ws

# Environment
VITE_ENVIRONMENT=development
VITE_APP_VERSION=1.0.0

# Feature Flags
VITE_FEATURE_ANALYTICS=true
VITE_FEATURE_VOICE_INPUT=true
VITE_FEATURE_EMOJI_Picker=true

# Security
VITE_JWT_SECRET=your_jwt_secret_key
VITE_ENCRYPTION_KEY=your_encryption_key
VITE_HMAC_SECRET=your_hmac_secret_key

# Analytics
VITE_GOOGLE_ANALYTICS_ID=your_google_analytics_id
VITE_PLAUSIBLE_DOMAIN=your_plausible_domain

# External Services
VITE_OPENAI_API_KEY=your_openai_api_key
VITE_ANTHROPIC_API_KEY=your_anthropic_api_key
VITE_SALESFORCE_API_URL=your_salesforce_api_url
VITE_SALESFORCE_CLIENT_ID=your_salesforce_client_id
VITE_SALESFORCE_CLIENT_SECRET=your_salesforce_client_secret
VITE_SALESFORCE_USERNAME=your_salesforce_username
VITE_SALESFORCE_PASSWORD=your_salesforce_password
VITE_SALESFORCE_SECURITY_TOKEN=your_salesforce_security_token

# Storage
VITE_STORAGE_PROVIDER=local
VITE_STORAGE_BUCKET=your_storage_bucket
VITE_STORAGE_REGION=your_storage_region
VITE_STORAGE_ACCESS_KEY=your_storage_access_key
VITE_STORAGE_SECRET_KEY=your_storage_secret_key

# Notifications
VITE_NOTIFICATION_SERVICE=none
VITE_PUSHOVER_USER_KEY=your_pushover_user_key
VITE_PUSHOVER_API_TOKEN=your_pushover_api_token
VITE_TWILIO_ACCOUNT_SID=your_twilio_account_sid
VITE_TWILIO_AUTH_TOKEN=your_twilio_auth_token
VITE_TWILIO_PHONE_NUMBER=your_twilio_phone_number

# Logging
VITE_LOG_LEVEL=debug
VITE_LOG_FORMAT=text
VITE_LOG_OUTPUT=console

# Performance
VITE_CACHE_ENABLED=true
VITE_CACHE_TTL=3600
VITE_CACHE_PROVIDER=memory
VITE_CACHE_REDIS_URL=redis://localhost:6379
VITE_CACHE_REDIS_PASSWORD=your_redis_password

# Internationalization
VITE_I18N_LOCALE=en
VITE_I18N_FALLBACK_LOCALE=en
VITE_I18N_LOCALES=en,es
```

## frontend/src/test/mocks.ts
```typescript
import { MockedResponse } from '@reduxjs/toolkit/query/react';
import { APIResponse } from '@store/types';

export const mockAuthResponse: MockedResponse<APIResponse<any>> = {
  status: 200,
  data: {
    user: {
      id: 'user123',
      email: 'test@example.com',
      displayName: 'Test User',
    },
    organization: {
      id: 'org123',
      name: 'Test Organization',
      subscriptionTier: 'free',
    },
    token: 'test-token',
    refreshToken: 'test-refresh-token',
    expiresAt: new Date(Date.now() + 3600000).toISOString(),
  },
};

export const mockConversationResponse: MockedResponse<APIResponse<Conversation>> = {
  status: 200,
  data: {
    id: 'conv123',
    organizationId: 'org123',
    userId: 'user123',
    conversationNumber: 1,
    title: 'Test Conversation',
    channel: 'web_chat',
    status: 'active',
    priority: 'medium',
    isUrgent: false,
    startedAt: new Date().toISOString(),
    lastActivityAt: new Date().toISOString(),
    messageCount: 2,
    aiHandled: true,
    resolved: false,
    escalated: false,
    language: 'en',
    tags: [],
    metadata: {},
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
};

export const mockMessagesResponse: MockedResponse<APIResponse<Message[]>> = {
  status: 200,
  data: [
    {
      id: 'msg1',
      conversationId: 'conv123',
      organizationId: 'org123',
      senderType: 'user',
      senderId: 'user123',
      senderName: 'Test User',
      content: 'Hello',
      contentType: 'text',
      createdAt: new Date().toISOString(),
      aiProcessed: false,
      isFlagged: false,
      isEdited: false,
      hasAttachments: false,
      attachments: [],
      metadata: {},
    },
    {
      id: 'msg2',
      conversationId: 'conv123',
      organizationId: 'org123',
      senderType: 'ai_agent',
      senderId: 'ai123',
      senderName: 'AI Assistant',
      content: 'Hi there!',
      contentType: 'text',
      createdAt: new Date().toISOString(),
      aiProcessed: true,
      isFlagged: false,
      isEdited: false,
      hasAttachments: false,
      attachments: [],
      metadata: {},
    },
  ],
};

export const mockError: MockedResponse<APIResponse<any>> = {
  status: 400,
  data: null,
  errors: [
    {
      code: 'BAD_REQUEST',
      message: 'Invalid request data',
      details: { field: 'email', reason: 'Invalid email format' },
      timestamp: new Date().toISOString(),
    },
  ],
};
```

## frontend/src/test/mockedData.ts
```typescript
import { User, Organization, Conversation, Message } from '@store/types';

export const mockUser: User = {
  id: 'user123',
  organizationId: 'org123',
  email: 'test@example.com',
  displayName: 'Test User',
  avatarUrl: 'https://example.com/avatar.png',
  role: 'customer',
  permissions: {},
  isActive: true,
  lastSeenAt: new Date().toISOString(),
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

export const mockOrganization: Organization = {
  id: 'org123',
  slug: 'test-org',
  name: 'Test Organization',
  subscriptionTier: 'free',
  settings: {
    aiEnabled: true,
    autoEscalation: true,
    sentimentAnalysis: true,
    emotionDetection: true,
    languageDetection: true,
    profanityFilter: true,
    autoTranslation: false,
  },
  features: {
    customModels: false,
    whiteLabel: false,
    ssoEnabled: false,
    apiAccess: true,
    webhooks: true,
    analyticsDashboard: true,
  },
  limits: {
    maxUsers: 10,
    maxConversationsPerMonth: 1000,
    maxMessagesPerConversation: 100,
    maxKnowledgeEntries: 1000,
    maxApiCallsPerHour: 10000,
    storageQuotaGb: 10,
  },
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

export const mockConversation: Conversation = {
  id: 'conv123',
  organizationId: 'org123',
  userId: 'user123',
  conversationNumber: 1,
  title: 'Test Conversation',
  channel: 'web_chat',
  status: 'active',
  priority: 'medium',
  isUrgent: false,
  startedAt: new Date().toISOString(),
  lastActivityAt: new Date().toISOString(),
  messageCount: 2,
  aiHandled: true,
  resolved: false,
  escalated: false,
  language: 'en',
  tags: [],
  metadata: {},
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

export const mockMessages: Message[] = [
  {
    id: 'msg1',
    conversationId: 'conv123',
    organizationId: 'org123',
    senderType: 'user',
    senderId: 'user123',
    senderName: 'Test User',
    content: 'Hello',
    contentType: 'text',
    createdAt: new Date().toISOString(),
    aiProcessed: false,
    isFlagged: false,
    isEdited: false,
    hasAttachments: false,
    attachments: [],
    metadata: {},
  },
  {
    id: 'msg2',
    conversationId: 'conv123',
    organizationId: 'org123',
    senderType: 'ai_agent',
    senderId: 'ai123',
    senderName: 'AI Assistant',
    content: 'Hi there!',
    contentType: 'text',
    createdAt: new Date().toISOString(),
    aiProcessed: true,
    isFlagged: false,
    isEdited: false,
    hasAttachments: false,
    attachments: [],
    metadata: {},
  },
];
```

## frontend/src/test/setupTests.ts
```typescript
import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock IntersectionObserver
class MockIntersectionObserver {
  constructor(callback: () => void) {
    this.callback = callback;
    this.observe = vi.fn();
    this.unobserve = vi.fn();
    this.disconnect = vi.fn();
  }
  
  callback: () => void;
  observe: () => void;
  unobserve: () => void;
  disconnect: () => void;
}

global.IntersectionObserver = MockIntersectionObserver as any;

// Mock WebSocket
class MockWebSocket {
  constructor(url: string) {
    this.url = url;
    this.readyState = WebSocket.CONNECTING;
    setTimeout(() => {
      this.onopen?.(new Event('open'));
      this.readyState = WebSocket.OPEN;
    }, 0);
  }
  
  url: string;
  readyState: number;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  
  send(data: string) {
    // Mock implementation
  }
  
  close(code?: number, reason?: string) {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close'));
  }
}

global.WebSocket = MockWebSocket as any;

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};

global.localStorage = localStorageMock as any;

// Mock sessionStorage
const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};

global.sessionStorage = sessionStorageMock as any;

// Mock Notification API
global.Notification = vi.fn().mockImplementation(() => ({
  close: vi.fn(),
}));

// Mock geolocation
global.navigator.geolocation = {
  getCurrentPosition: vi.fn(),
  watchPosition: vi.fn(),
  clearWatch: vi.fn(),
};

// Mock media devices
global.navigator.mediaDevices = {
  getUserMedia: vi.fn().mockResolvedValue({
    getTracks: () => [],
  }),
  enumerateDevices: vi.fn().mockResolvedValue([]),
};

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: {
      language: 'en',
      changeLanguage: vi.fn(),
    },
  }),
  Trans: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock React Router
vi.mock('react-router-dom', () => ({
  ...vi.importActual('react-router-dom'),
  useParams: () => ({ conversationId: 'conv123' }),
  useNavigate: () => vi.fn(),
  useLocation: () => ({ pathname: '/chat/conv123' }),
}));

// Mock API responses
vi.mock('@store/api', () => ({
  authAPI: {
    login: vi.fn().mockResolvedValue(mockAuthResponse),
    refreshToken: vi.fn().mockResolvedValue(mockAuthResponse),
    getCurrentUser: vi.fn().mockResolvedValue(mockAuthResponse),
  },
  conversationAPI: {
    getConversations: vi.fn().mockResolvedValue(mockConversationResponse),
    getConversation: vi.fn().mockResolvedValue(mockConversationResponse),
    getMessages: vi.fn().mockResolvedValue(mockMessagesResponse),
    createConversation: vi.fn().mockResolvedValue(mockConversationResponse),
    sendMessage: vi.fn().mockResolvedValue(mockMessagesResponse[0]),
  },
}));

// Mock services
vi.mock('@services/websocket/websocketService', () => ({
  websocketService: {
    send: vi.fn(),
    getConnectionStatus: vi.fn().mockReturnValue('connected'),
  },
}));

// Mock utilities
vi.mock('@utils/messageUtils', () => ({
  formatMessageTime: vi.fn().mockImplementation((timestamp) => timestamp),
  groupMessagesByDate: vi.fn().mockImplementation((messages) => messages),
  getMessageTypeIcon: vi.fn().mockReturnValue('📝'),
  sanitizeMessageContent: vi.fn().mockImplementation((content) => content),
  getSentimentEmoji: vi.fn().mockReturnValue('😐'),
  getEmotionEmoji: vi.fn().mockReturnValue('😐'),
  shouldShowTimestamp: vi.fn().mockReturnValue(true),
  isSameSender: vi.fn().mockReturnValue(true),
  isConsecutiveMessage: vi.fn().mockReturnValue(true),
  extractTextFromHTML: vi.fn().mockImplementation((html) => html),
  truncateMessage: vi.fn().mockImplementation((content) => content),
  containsProfanity: vi.fn().mockReturnValue(false),
  filterProfanity: vi.fn().mockImplementation((content) => content),
  generateMessageSummary: vi.fn().mockReturnValue('Summary'),
  calculateMessageStats: vi.fn().mockReturnValue({
    total: 0,
    bySender: {},
    byContentType: {},
    averageLength: 0,
  }),
}));
```

## frontend/src/test/mocks.ts
```typescript
import { APIResponse } from '@store/types';

export const mockAuthResponse: APIResponse<any> = {
  data: {
    user: {
      id: 'user123',
      email: 'test@example.com',
      displayName: 'Test User',
    },
    organization: {
      id: 'org123',
      name: 'Test Organization',
      subscriptionTier: 'free',
    },
    token: 'test-token',
    refreshToken: 'test-refresh-token',
    expiresAt: new Date(Date.now() + 3600000).toISOString(),
  },
  status: 200,
};

export const mockConversationResponse: APIResponse<Conversation> = {
  data: {
    id: 'conv123',
    organizationId: 'org123',
    userId: 'user123',
    conversationNumber: 1,
    title: 'Test Conversation',
    channel: 'web_chat',
    status: 'active',
    priority: 'medium',
    isUrgent: false,
    startedAt: new Date().toISOString(),
    lastActivityAt: new Date().toISOString(),
    messageCount: 2,
    aiHandled: true,
    resolved: false,
    escalated: false,
    language: 'en',
    tags: [],
    metadata: {},
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  status: 200,
};

export const mockMessagesResponse: APIResponse<Message[]> = {
  data: [
    {
      id: 'msg1',
      conversationId: 'conv123',
      organizationId: 'org123',
      senderType: 'user',
      senderId: 'user123',
      senderName: 'Test User',
      content: 'Hello',
      contentType: 'text',
      createdAt: new Date().toISOString(),
      aiProcessed: false,
      isFlagged: false,
      isEdited: false,
      hasAttachments: false,
      attachments: [],
      metadata: {},
    },
    {
      id: 'msg2',
      conversationId: 'conv123',
      organizationId: 'org123',
      senderType: 'ai_agent',
      senderId: 'ai123',
      senderName: 'AI Assistant',
      content: 'Hi there!',
      contentType: 'text',
      createdAt: new Date().toISOString(),
      aiProcessed: true,
      isFlagged: false,
      isEdited: false,
      hasAttachments: false,
      attachments: [],
      metadata: {},
    },
  ],
  status: 200,
};

export const mockError: APIResponse<any> = {
  data: null,
  status: 400,
  errors: [
    {
      code: 'BAD_REQUEST',
      message: 'Invalid request data',
      details: { field: 'email', reason: 'Invalid email format' },
      timestamp: new Date().toISOString(),
    },
  ],
};
```

## frontend/src/test/mockedData.ts
```typescript
import { User, Organization, Conversation, Message } from '@store/types';

export const mockUser: User = {
  id: 'user123',
  organizationId: 'org123',
  email: 'test@example.com',
  displayName: 'Test User',
  avatarUrl: 'https://example.com/avatar.png',
  role: 'customer',
  permissions: {},
  isActive: true,
  lastSeenAt: new Date().toISOString(),
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

export const mockOrganization: Organization = {
  id: 'org123',
  slug: 'test-org',
  name: 'Test Organization',
  subscriptionTier: 'free',
  settings: {
    aiEnabled: true,
    autoEscalation: true,
    sentimentAnalysis: true,
    emotionDetection: true,
    languageDetection: true,
    profanityFilter: true,
    autoTranslation: false,
  },
  features: {
    customModels: false,
    whiteLabel: false,
    ssoEnabled: false,
    apiAccess: true,
    webhooks: true,
    analyticsDashboard: true,
  },
  limits: {
    maxUsers: 10,
    maxConversationsPerMonth: 1000,
    maxMessagesPerConversation: 100,
    maxKnowledgeEntries: 1000,
    maxApiCallsPerHour: 10000,
    storageQuotaGb: 10,
  },
  createdAt: new
