'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ChatSidebar } from '@/components/chat-sidebar'
import { ChatPanel } from '@/components/chat-panel'
import { useRagChat } from '@/hooks/use-rag-chat'

export default function ChatPage() {
  const router = useRouter()
  const [token, setToken] = useState<string | null>(null)
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

  const chat = useRagChat(token || undefined)

  useEffect(() => {
    // Get token from localStorage
    const storedToken = localStorage.getItem('auth_token')
    if (!storedToken) {
      router.push('/')
      return
    }
    setToken(storedToken)
  }, [router])

  useEffect(() => {
    if (token) {
      chat.connect()
    }
  }, [token, chat])

  if (!token) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-muted">Loading...</div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Sidebar */}
      <ChatSidebar
        isOpen={isSidebarOpen}
        onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
        messages={chat.messages}
        token={token}
        onNewChat={chat.clearMessages}
        onLogout={() => {
          localStorage.removeItem('auth_token')
          chat.disconnect()
          router.push('/')
        }}
      />

      {/* Main Chat Panel */}
      <ChatPanel
        messages={chat.messages}
        isStreaming={chat.isStreaming}
        connectionStatus={chat.connectionStatus}
        onSendMessage={chat.sendMessage}
        isSidebarOpen={isSidebarOpen}
        onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
      />
    </div>
  )
}