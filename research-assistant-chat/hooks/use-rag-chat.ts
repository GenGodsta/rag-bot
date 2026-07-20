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

type RagChatState = {
  messages: Message[]
  isConnected: boolean
  isStreaming: boolean
  connectionStatus: 'connected' | 'connecting' | 'disconnected' | 'error'
  error?: string
}

export function useRagChat(token?: string) {
  const wsRef = useRef<WebSocket | null>(null)
  const [state, setState] = useState<RagChatState>({
    messages: [],
    isConnected: false,
    isStreaming: false,
    connectionStatus: 'disconnected',
  })

  const connect = useCallback(() => {
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
    }))

    try {
      const wsBase = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api/chat/ws/chat'
      const wsUrl = `${wsBase}?token=${encodeURIComponent(token)}`
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
  }, [token])

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
    }))
  }, [])

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
  }
}