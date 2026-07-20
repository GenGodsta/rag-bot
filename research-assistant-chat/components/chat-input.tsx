'use client'

import { useRef, useState } from 'react'
import { Send } from 'lucide-react'

interface ChatInputProps {
  onSendMessage: (query: string) => void
  isDisabled: boolean
  isStreaming: boolean
}

export function ChatInput({
  onSendMessage,
  isDisabled,
  isStreaming,
}: ChatInputProps) {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    const trimmed = input.trim()
    if (trimmed && !isDisabled) {
      onSendMessage(trimmed)
      setInput('')
      if (textareaRef.current) {
        textareaRef.current.style.height = '44px'
      }
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Check for IME composition to handle CJK input correctly
    if (e.nativeEvent.isComposing || e.keyCode === 229) {
      return
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    } else if (e.key === 'Enter' && e.shiftKey) {
      // Allow shift+enter for newline
      e.preventDefault()
      const start = textareaRef.current?.selectionStart || 0
      const end = textareaRef.current?.selectionEnd || 0
      const value = input
      setInput(value.substring(0, start) + '\n' + value.substring(end))
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)

    // Auto-resize textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = '44px'
      const scrollHeight = textareaRef.current.scrollHeight
      textareaRef.current.style.height = Math.min(scrollHeight, 200) + 'px'
    }
  }

  return (
    <div className="border-t border-border bg-background px-4 py-4 max-w-4xl mx-auto w-full">
      <div className="flex gap-3">
        <div className="flex-1 flex gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Ask a research question... (Shift+Enter for new line)"
            disabled={isDisabled}
            rows={1}
            className="flex-1 px-4 py-2.5 bg-surface border border-border rounded-lg text-foreground placeholder-muted text-sm resize-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed hover:border-border focus:border-accent focus:ring-1 focus:ring-accent/20"
          />
        </div>

        <button
          onClick={handleSend}
          disabled={isDisabled || !input.trim()}
          aria-label="Send message"
          className="flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-lg bg-accent hover:bg-accent-hover text-background transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>

      {isStreaming && (
        <p className="text-xs text-muted mt-2">
          ✓ Streaming response... (input disabled)
        </p>
      )}
    </div>
  )
}
