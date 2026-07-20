'use client'

import { useRef, useEffect } from 'react'
import { WifiOff, Wifi, AlertCircle } from 'lucide-react'
import { MessageBubble } from './message-bubble'
import { ChatInput } from './chat-input'
import { TopBar } from './top-bar'
import type { Message } from '@/hooks/use-rag-chat'

interface ChatPanelProps {
  messages: Message[]
  isStreaming: boolean
  connectionStatus: 'connected' | 'connecting' | 'disconnected' | 'error'
  onSendMessage: (query: string, topk?: number) => void
  isSidebarOpen: boolean
  onToggleSidebar: () => void
}

export function ChatPanel({
  messages,
  isStreaming,
  connectionStatus,
  onSendMessage,
  isSidebarOpen,
  onToggleSidebar,
}: ChatPanelProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-background">
      {/* Top Bar */}
      <TopBar
        connectionStatus={connectionStatus}
        isSidebarOpen={isSidebarOpen}
        onToggleSidebar={onToggleSidebar}
      />

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto px-4 py-6 max-w-4xl mx-auto w-full">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center py-20">
            <div className="w-12 h-12 rounded-full bg-surface mb-4 flex items-center justify-center">
              <Wifi className="w-6 h-6 text-accent" />
            </div>
            <h2 className="text-xl font-semibold text-foreground mb-2">
              Welcome to Research Assistant
            </h2>
            <p className="text-muted max-w-md mb-8">
              Ask me anything about your research topics. I&apos;ll search through our knowledge base
              and provide answers with citations.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} isStreaming={message.streaming} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <ChatInput
        onSendMessage={onSendMessage}
        isDisabled={!connectionStatus || connectionStatus !== 'connected' || isStreaming}
        isStreaming={isStreaming}
      />
    </div>
  )
}
