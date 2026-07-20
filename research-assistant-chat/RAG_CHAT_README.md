# RAG-Based Chat UI Frontend

A modern, responsive React/TypeScript chat interface for RAG (Retrieval-Augmented Generation) research assistants with real-time streaming responses and citation management.

## Features

✅ **Clean Dark Theme** — Technical, minimal aesthetic inspired by Linear and Vercel dashboards
✅ **Real-time Streaming** — Token-by-token response streaming with animated typing cursor
✅ **Citation Management** — Collapsible source panels distinguishing between book and web citations
✅ **WebSocket Integration** — Custom `useRagChat` hook for easy backend connection
✅ **Responsive Design** — Works seamlessly on desktop and mobile
✅ **Connection Status** — Visual indicators for WebSocket connection state (connected, connecting, error)
✅ **Chat History Sidebar** — Conversation management with new chat button
✅ **Input Validation** — Multiline textarea with Shift+Enter support and IME composition handling

## Project Structure

```
app/
├── page.tsx              # Login page
├── chat/
│   ├── page.tsx         # Chat container & page layout
│   └── layout.tsx       # Chat layout wrapper
├── layout.tsx           # Root layout
└── globals.css          # Dark theme & styling

components/
├── chat-sidebar.tsx     # Left sidebar with chat history
├── chat-panel.tsx       # Main chat container
├── message-bubble.tsx   # Message UI with sources
├── chat-input.tsx       # Input textarea & send button
└── top-bar.tsx          # Connection status header

hooks/
└── use-rag-chat.ts      # WebSocket connection & state management
```

## Backend Integration

The frontend is built to match the exact backend contract. To connect to your FastAPI backend:

### 1. Update WebSocket URL

In `hooks/use-rag-chat.ts`, line ~48:

```typescript
const wsUrl = `ws://localhost:8000/ws/chat?token=${encodeURIComponent(token)}`
```

Change the hostname and port to match your FastAPI server.

### 2. Update Login Endpoint

In `app/page.tsx`, line ~30:

```typescript
const response = await fetch('/login', {
```

Change to your actual login endpoint:

```typescript
const response = await fetch('http://your-backend.com/login', {
```

### 3. Environment Variables (Optional)

Create a `.env.local` file to configure backend URLs:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/chat
```

Then update the hooks to use these variables:

```typescript
const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}?token=${encodeURIComponent(token)}`
```

## Backend Contract

The frontend expects your FastAPI backend to implement:

### Login Endpoint

```
POST /login
Content-Type: application/json

Request:
{
  "email": "user@example.com",
  "password": "password123"
}

Response:
{
  "token": "jwt-token-here",
  "access_token": "jwt-token-here"  # or use either key
}
```

### WebSocket Chat Endpoint

```
ws://localhost:8000/ws/chat?token=<JWT>

Client sends (JSON):
{
  "query": "What is X?",
  "topk": 5  # Optional, defaults to 5
}

Server streams text tokens one at a time, then sends:
__DONE__:{
  "done": true,
  "sources": [
    {
      "source": "Book Title or URL",
      "page": "45" or "Web",
      "score": 0.95,
      "preview": "Truncated excerpt from the source..."
    }
  ]
}

On error, server sends:
__DONE__:{
  "error": "Error message here"
}
```

## Message Format & Types

```typescript
// Message stored in state
type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  streaming?: boolean
  error?: string
}

// Citation source
type Source = {
  source: string      # Book title or URL
  page: string       # Page number (for books) or "Web" (for web results)
  score: number      # Relevance score 0-1
  preview: string    # Truncated excerpt
}
```

## Usage

### Development

```bash
# Install dependencies
pnpm install

# Start dev server
pnpm dev

# Build for production
pnpm build

# Start production server
pnpm start
```

Visit `http://localhost:3000`

### Using the useRagChat Hook

```typescript
import { useRagChat } from '@/hooks/use-rag-chat'

export function MyComponent() {
  const chat = useRagChat(token)

  // Connect to WebSocket
  useEffect(() => {
    if (token) {
      chat.connect()
    }
  }, [token, chat])

  // Send a message
  const handleSend = (query: string) => {
    chat.sendMessage(query, 5) // topk=5
  }

  return (
    <div>
      <p>Status: {chat.connectionStatus}</p>
      {chat.messages.map(msg => (
        <div key={msg.id}>{msg.content}</div>
      ))}
    </div>
  )
}
```

## Design System

### Colors

- **Background**: `#1a1a1a` (deep black)
- **Surface**: `#262626` (dark gray)
- **Accent**: `#0ea5e9` (cyan blue)
- **Border**: `#3f3f3f` (subtle gray)
- **Foreground**: `#ffffff` (white)
- **Muted**: `#a3a3a3` (medium gray)

### Typography

- **Fonts**: Geist (default), Geist Mono (code)
- **Body text**: `text-sm` (14px)
- **Headings**: `text-base`/`text-lg`/`text-2xl`

### Responsive Breakpoints

- Mobile: < 768px (sidebar becomes overlay)
- Desktop: ≥ 768px (sidebar always visible)

## Key Implementation Details

### Streaming Response Handling

The backend streams response tokens one at a time. The frontend:

1. Creates an empty assistant message bubble
2. Appends each token to the message content as it arrives
3. Shows animated typing cursor while streaming
4. Receives final `__DONE__` message with sources
5. Displays sources in expandable collapsible panel

### Book vs Web Citations

Sources are differentiated by the `page` field:

- If `page` is a number or string (not "Web"), it's treated as a book citation with "📖 Books" badge
- If `page` is "Web", it's treated as a web result with "🌐 Web" badge

### Connection States

The UI displays connection status with visual indicators:

- ✅ **Connected** — Green indicator, input enabled
- 🔄 **Connecting** — Yellow indicator, input disabled
- ❌ **Disconnected** — Gray indicator, input disabled
- ⚠️ **Error** — Red indicator with error message

### Input Handling

The textarea component includes:

- Auto-resize as user types (min 44px, max 200px)
- Shift+Enter for multiline input, Enter to send
- IME composition detection (handles CJK input correctly)
- Disabled state while response is streaming
- Clear on successful send

## Customization

### Theming

To change colors, edit the CSS variables in `app/globals.css`:

```css
@theme {
  --color-background: #1a1a1a;
  --color-accent: #0ea5e9;
  /* ... */
}
```

### Component Styling

All components use Tailwind CSS with the design tokens. Update component classes directly for minor adjustments.

### Error Handling

Errors are displayed inline within message bubbles. For more robust error handling, modify the `useRagChat` hook to implement retry logic or error recovery.

## Browser Support

- Chrome/Edge: ✅ Latest 2 versions
- Firefox: ✅ Latest 2 versions
- Safari: ✅ Latest 2 versions
- Mobile browsers: ✅ iOS Safari, Chrome Mobile

## Performance Notes

- WebSocket messages are processed in real-time with zero debounce
- Scrolling is optimized with `scroll-behavior: smooth`
- Message list auto-scrolls on new messages
- Textarea auto-resizes without layout thrash
- No unnecessary re-renders (hooks are memoized)

## Deployment

### Vercel

```bash
vercel deploy
```

Set environment variables in Vercel project settings:

```
NEXT_PUBLIC_API_URL=https://your-api.com
NEXT_PUBLIC_WS_URL=wss://your-api.com/ws/chat
```

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY . .
RUN pnpm install
RUN pnpm build
EXPOSE 3000
CMD ["pnpm", "start"]
```

### Other Platforms

This is a standard Next.js 16 application. Deploy to any platform supporting Node.js 18+.

## Troubleshooting

### WebSocket Connection Fails

1. Verify backend is running and endpoint is correct
2. Check CORS settings on backend
3. Ensure JWT token is valid
4. Look for connection errors in browser DevTools Console

### Messages Don't Stream

1. Check WebSocket message format in browser DevTools Network tab
2. Verify backend is sending tokens one per message
3. Ensure `__DONE__` message is being sent after stream completes
4. Check for `isComposing` flag in IME handling

### Layout Issues on Mobile

1. Check viewport is set in `<meta name="viewport">`
2. Verify Tailwind breakpoints (md: 768px)
3. Test sidebar toggle functionality
4. Check for content overflow in message bubbles

## License

MIT
