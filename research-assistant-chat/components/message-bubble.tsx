'use client'

import { useState } from 'react'
import { ChevronDown, BookOpen, Globe, AlertCircle } from 'lucide-react'
import type { Message } from '@/hooks/use-rag-chat'

interface MessageBubbleProps {
  message: Message
  isStreaming?: boolean
}

export function MessageBubble({ message, isStreaming = false }: MessageBubbleProps) {
  const [sourcesExpanded, setSourcesExpanded] = useState(false)
  const isUser = message.role === 'user'

  // Check if response is from books or web
  const hasBookSources = message.sources?.some((s) => s.page !== 'Web')
  const hasWebSources = message.sources?.some((s) => s.page === 'Web')

  return (
    <div className={`flex gap-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {/* Avatar */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded bg-surface border border-border flex items-center justify-center">
          <span className="text-xs font-semibold text-accent">AI</span>
        </div>
      )}

      {/* Message Content */}
      <div className={`flex-shrink-0 max-w-xl ${isUser ? 'max-w-md' : ''}`}>
        {/* Badges */}
        {!isUser && (message.sources?.length ?? 0) > 0 && (
          <div className="flex gap-2 mb-2">
            {hasBookSources && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-surface border border-border rounded text-xs text-muted">
                <BookOpen className="w-3 h-3" />
                Books
              </span>
            )}
            {hasWebSources && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-surface border border-border rounded text-xs text-muted">
                <Globe className="w-3 h-3" />
                Web
              </span>
            )}
          </div>
        )}

        {/* Message Bubble */}
        <div
          className={`px-4 py-3 rounded-lg border ${
            isUser
              ? 'bg-accent text-background border-accent'
              : 'bg-surface border-border text-foreground'
          }`}
        >
          <p className="text-sm whitespace-pre-wrap break-words leading-relaxed">
            {message.content}
            {isStreaming && <span className="typing-cursor" />}
          </p>

          {/* Error State */}
          {message.error && (
            <div className="mt-3 p-2 bg-error/10 border border-error rounded flex gap-2">
              <AlertCircle className="w-4 h-4 text-error flex-shrink-0 mt-0.5" />
              <p className="text-xs text-error">{message.error}</p>
            </div>
          )}
        </div>

        {/* Sources */}
        {!isUser && !isStreaming && (message.sources?.length ?? 0) > 0 && (
          <div className="mt-3">
            <button
              onClick={() => setSourcesExpanded(!sourcesExpanded)}
              className="flex items-center gap-2 text-xs text-muted hover:text-foreground transition-colors"
            >
              <ChevronDown
                className={`w-4 h-4 transition-transform ${sourcesExpanded ? 'rotate-180' : ''}`}
              />
              Sources ({message.sources?.length})
            </button>

            {sourcesExpanded && (
              <div className="mt-2 space-y-2">
                {message.sources?.map((source, idx) => {
                  const isBook = source.page !== 'Web'
                  return (
                    <div
                      key={idx}
                      className="p-3 bg-surface border border-border rounded-md hover:border-accent transition-colors group cursor-default"
                    >
                      <div className="flex items-start gap-2">
                        {isBook ? (
                          <BookOpen className="w-4 h-4 text-muted flex-shrink-0 mt-0.5" />
                        ) : (
                          <Globe className="w-4 h-4 text-muted flex-shrink-0 mt-0.5" />
                        )}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-foreground truncate">
                            {source.source}
                          </p>
                          {isBook && (
                            <p className="text-xs text-muted">p. {source.page}</p>
                          )}
                          {!isBook && (
                            <p className="text-xs text-muted">Web</p>
                          )}
                          <p className="text-xs text-muted mt-2 line-clamp-2">
                            {source.preview}
                          </p>
                          <p className="text-xs text-accent mt-1">
                            Relevance: {(source.score * 100).toFixed(0)}%
                          </p>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* User Avatar */}
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded bg-accent flex items-center justify-center">
          <span className="text-xs font-semibold text-background">U</span>
        </div>
      )}
    </div>
  )
}
