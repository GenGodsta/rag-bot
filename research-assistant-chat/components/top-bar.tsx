'use client'

import { Menu, Wifi, AlertCircle, WifiOff } from 'lucide-react'

interface TopBarProps {
  connectionStatus: 'connected' | 'connecting' | 'disconnected' | 'error'
  isSidebarOpen: boolean
  onToggleSidebar: () => void
}

export function TopBar({
  connectionStatus,
  isSidebarOpen,
  onToggleSidebar,
}: TopBarProps) {
  const getStatusDisplay = () => {
    switch (connectionStatus) {
      case 'connected':
        return {
          icon: Wifi,
          label: 'Connected',
          color: 'text-green-400',
          bgColor: 'bg-green-400/10',
        }
      case 'connecting':
        return {
          icon: Wifi,
          label: 'Connecting...',
          color: 'text-yellow-400',
          bgColor: 'bg-yellow-400/10',
        }
      case 'disconnected':
        return {
          icon: WifiOff,
          label: 'Disconnected',
          color: 'text-muted',
          bgColor: 'bg-surface',
        }
      case 'error':
        return {
          icon: AlertCircle,
          label: 'Connection Error',
          color: 'text-error',
          bgColor: 'bg-error/10',
        }
    }
  }

  const status = getStatusDisplay()
  const StatusIcon = status.icon

  return (
    <div className="border-b border-border bg-surface px-4 py-3 flex items-center justify-between">
      {/* Left: Menu button (mobile) + Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="hidden md:inline-flex p-2 hover:bg-surface-hover rounded transition-colors"
          aria-label="Toggle sidebar"
        >
          <Menu className="w-5 h-5 text-foreground" />
        </button>
        <h1 className="text-base font-semibold text-foreground">Research Assistant</h1>
      </div>

      {/* Right: Connection status */}
      <div className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium ${status.color} ${status.bgColor}`}>
        <StatusIcon className="w-3.5 h-3.5" />
        {status.label}
      </div>
    </div>
  )
}
