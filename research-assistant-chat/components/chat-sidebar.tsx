'use client'

import { useEffect, useState } from 'react'
import { Plus, LogOut, Menu, X } from 'lucide-react'
import type { Message } from '@/hooks/use-rag-chat'

interface HistoryRecord {
  query: string
  answer: string
  sources: unknown[]
  timestamp: string
  session_id: string
}

interface SessionSummary {
  session_id: string
  title: string
  timestamp: string
}

interface ChatSidebarProps {
  isOpen: boolean
  onToggle: () => void
  messages: Message[]
  onLogout: () => void
  token: string
  onNewChat: () => void
  onSelectSession: (sessionId: string) => void
  activeSessionId?: string | null
}

function formatDay(timestamp: string) {
  const date = new Date(timestamp)
  const today = new Date()
  const isToday = date.toDateString() === today.toDateString()
  if (isToday) return 'Today'
  const yesterday = new Date(today)
  yesterday.setDate(today.getDate() - 1)
  if (date.toDateString() === yesterday.toDateString()) return 'Yesterday'
  return date.toLocaleDateString()
}

export function ChatSidebar({
  isOpen,
  onToggle,
  messages,
  onLogout,
  token,
  onNewChat,
  onSelectSession,
  activeSessionId,
}: ChatSidebarProps) {
  const [history, setHistory] = useState<HistoryRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!token) return

    const fetchHistory = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/history/?limit=20`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (!response.ok) return
        const data = await response.json()
        setHistory(data.history || [])
      } catch {
        // silently fail — sidebar just shows current session only
      } finally {
        setIsLoading(false)
      }
    }

    fetchHistory()
  }, [token, messages.length])

  // Generate conversation title from first user message in the current session
  const getConversationTitle = () => {
    const firstUserMessage = messages.find((m) => m.role === 'user')
    if (!firstUserMessage) return 'New chat'
    const text = firstUserMessage.content
    return text.length > 30 ? text.substring(0, 30) + '...' : text
  }

  const hasMessages = messages.length > 0

  // Group flat history records into one entry per session_id.
  // history is sorted newest-first from the API; walking through in
  // order and overwriting title on repeat visits leaves the EARLIEST
  // query in that session as the final title (used as the chat name).
  const sessionMap = new Map<string, SessionSummary>()
  for (const record of history) {
    const existing = sessionMap.get(record.session_id)
    if (!existing) {
      sessionMap.set(record.session_id, {
        session_id: record.session_id,
        title: record.query,
        timestamp: record.timestamp,
      })
    } else {
      existing.title = record.query
    }
  }
  const groupedSessions = Array.from(sessionMap.values())

  return (
    <>
      {/* Mobile Toggle Button */}
      <button
        onClick={onToggle}
        className="md:hidden fixed top-4 left-4 z-50 p-2 hover:bg-surface rounded transition-colors"
        aria-label="Toggle sidebar"
      >
        {isOpen ? (
          <X className="w-5 h-5 text-foreground" />
        ) : (
          <Menu className="w-5 h-5 text-foreground" />
        )}
      </button>

      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="md:hidden fixed inset-0 bg-background/80 z-40"
          onClick={onToggle}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } fixed md:relative md:translate-x-0 left-0 top-0 h-screen w-64 bg-surface border-r border-border flex flex-col transition-transform duration-200 z-40`}
      >
        {/* Header */}
        <div className="p-4 border-b border-border">
          <button
            onClick={onNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover text-background font-medium rounded text-sm transition-colors"
          >
            <Plus className="w-4 h-4" />
            New chat
          </button>
        </div>

        {/* Conversations */}
        <div className="flex-1 overflow-y-auto py-4">
          {hasMessages && !activeSessionId && (
            <div className="px-3 space-y-2 mb-2">
              <p className="px-3 text-xs text-muted uppercase tracking-wide">Current session</p>
              <div className="px-3 py-2 rounded bg-surface-hover">
                <p className="text-sm text-foreground font-medium truncate">
                  {getConversationTitle()}
                </p>
                <p className="text-xs text-muted">Now</p>
              </div>
            </div>
          )}

          {isLoading && (
            <p className="px-4 py-2 text-xs text-muted">Loading history...</p>
          )}

          {!isLoading && groupedSessions.length > 0 && (
            <div className="px-3 space-y-2">
              <p className="px-3 text-xs text-muted uppercase tracking-wide">Past questions</p>
              {groupedSessions.map((session) => {
                const isActive = session.session_id === activeSessionId
                return (
                  <button
                    key={session.session_id}
                    onClick={() => onSelectSession(session.session_id)}
                    title={session.title}
                    className={`w-full text-left px-3 py-2 rounded transition-colors ${
                      isActive ? 'bg-surface-hover' : 'hover:bg-surface-hover'
                    }`}
                  >
                    <p className="text-sm text-foreground truncate">
                      {session.title.length > 30
                        ? session.title.substring(0, 30) + '...'
                        : session.title}
                    </p>
                    <p className="text-xs text-muted">{formatDay(session.timestamp)}</p>
                  </button>
                )
              })}
            </div>
          )}

          {!isLoading && groupedSessions.length === 0 && !hasMessages && (
            <div className="px-4 py-8 text-center">
              <p className="text-sm text-muted">No conversations yet</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border space-y-2">
          <button
            onClick={onLogout}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 text-muted hover:text-foreground hover:bg-surface-hover rounded text-sm transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
          <p className="text-xs text-muted text-center">v1.0</p>
        </div>
      </aside>
    </>
  )
}