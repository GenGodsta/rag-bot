'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

export type Source = {
  source: string
  page: string
  score: number
  preview: string
}

export type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  streaming?: boolean
  error?: string
}

type HistoryTurn = {
  query: string
  answer: string
  sources: Source[]
  timestamp: string
  session_id: string
}

type RagChatState = {
  messages: Message[]
  isConnected: boolean
  isStreaming: boolean
  connectionStatus: 'connected' | 'connecting' | 'disconnected' | 'error'
  error?: string
  sessionId: string | null
}

export function useRagChat(token?: string) {
  const wsRef = useRef<WebSocket | null>(null)
  const [state, setState] = useState<RagChatState>({
    messages: [],
    isConnected: false,
    isStreaming: false,
    connectionStatus: 'disconnected',
    sessionId: null,
  })

  const connect = useCallback(
    (resumeSessionId?: string) => {
      if (!token) return

      // Don't open a second connection if one is already open or in progress
      if (
        wsRef.current &&
        (wsRef.current.readyState === WebSocket.OPEN ||
          wsRef.current.readyState === WebSocket.CONNECTING)
      ) {
        return
      }

      setState((prev) => ({
        ...prev,
        connectionStatus: 'connecting',
        sessionId: resumeSessionId ?? null,
      }))

      try {
        const wsBase = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api/chat/ws/chat'
        const params = new URLSearchParams({ token })
        if (resumeSessionId) params.set('session_id', resumeSessionId)
        const wsUrl = `${wsBase}?${params.toString()}`
        const ws = new WebSocket(wsUrl)

        ws.onopen = () => {
          setState((prev) => ({
            ...prev,
            isConnected: true,
            connectionStatus: 'connected',
            error: undefined,
          }))
        }

        ws.onmessage = (event) => {
          const message = event.data

          if (message.startsWith('__DONE__:')) {
            const jsonStr = message.substring('__DONE__:'.length)
            const data = JSON.parse(jsonStr)

            setState((prev) => {
              const lastMessage = prev.messages[prev.messages.length - 1]
              if (lastMessage && lastMessage.role === 'assistant') {
                const updatedMessages = [...prev.messages]
                updatedMessages[updatedMessages.length - 1] = {
                  ...lastMessage,
                  streaming: false,
                  sources: data.sources || [],
                  error: data.error,
                }
                return {
                  ...prev,
                  messages: updatedMessages,
                  isStreaming: false,
                }
              }
              return prev
            })
          } else {
            setState((prev) => {
              const messages = [...prev.messages]
              const lastMessage = messages[messages.length - 1]

              if (lastMessage && lastMessage.role === 'assistant') {
                messages[messages.length - 1] = {
                  ...lastMessage,
                  content: lastMessage.content + message,
                }
              }

              return {
                ...prev,
                messages,
              }
            })
          }
        }

        ws.onerror = () => {
          setState((prev) => ({
            ...prev,
            connectionStatus: 'error',
            error: 'WebSocket connection error',
          }))
        }

        ws.onclose = () => {
          setState((prev) => ({
            ...prev,
            isConnected: false,
            connectionStatus: 'disconnected',
          }))
        }

        wsRef.current = ws
      } catch (err) {
        setState((prev) => ({
          ...prev,
          connectionStatus: 'error',
          error: err instanceof Error ? err.message : 'Connection failed',
        }))
      }
    },
    [token]
  )

  const sendMessage = useCallback(
    (query: string, topk: number = 5) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        return
      }

      // Add user message
      const userMessage: Message = {
        id: `msg-${Date.now()}`,
        role: 'user',
        content: query,
      }

      // Add empty assistant message that will stream in
      const assistantMessage: Message = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: '',
        streaming: true,
      }

      setState((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage, assistantMessage],
        isStreaming: true,
      }))

      // Send to server
      wsRef.current.send(JSON.stringify({ query, topk }))
    },
    []
  )

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  const clearMessages = useCallback(() => {
    setState((prev) => ({
      ...prev,
      messages: [],
      sessionId: null,
    }))
  }, [])

  // Fetch a past session's turns, load them into messages state, then
  // (re)connect the socket bound to that same session_id so sending a
  // new message continues the conversation instead of starting a new one.
  const loadSession = useCallback(
    async (sessionId: string) => {
      if (!token) return

      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/history/${sessionId}`,
          { headers: { Authorization: `Bearer ${token}` } }
        )
        if (!response.ok) return
        const data: { session_id: string; turns: HistoryTurn[] } = await response.json()

        const loadedMessages: Message[] = data.turns.flatMap((turn, idx) => [
          {
            id: `hist-user-${idx}`,
            role: 'user' as const,
            content: turn.query,
          },
          {
            id: `hist-assistant-${idx}`,
            role: 'assistant' as const,
            content: turn.answer,
            sources: turn.sources,
            streaming: false,
          },
        ])

        setState((prev) => ({
          ...prev,
          messages: loadedMessages,
          sessionId,
        }))

        disconnect()
        connect(sessionId)
      } catch {
        // silently fail — leave current state as-is
      }
    },
    [token, connect, disconnect]
  )

  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return {
    ...state,
    connect,
    sendMessage,
    disconnect,
    clearMessages,
    loadSession,
  }
}