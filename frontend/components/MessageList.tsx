'use client'

import { useEffect, useRef } from 'react'
import { User, Bot, MapPin, Clock } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: string
  mapsData?: any
}

interface MessageListProps {
  messages: Message[]
}

export default function MessageList({ messages }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const renderMapsInfo = (mapsData: any) => {
    if (!mapsData) return null

    if (mapsData.places && mapsData.places.length > 0) {
      return (
        <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="flex items-center space-x-2 mb-2">
            <MapPin className="w-4 h-4 text-blue-600" />
            <span className="text-sm font-medium text-blue-800 dark:text-blue-200">
              Found {mapsData.places.length} places
            </span>
          </div>
          
          <div className="space-y-2">
            {mapsData.places.slice(0, 3).map((place: any, index: number) => (
              <div key={place.place_id || index} className="text-sm">
                <div className="font-medium text-gray-900 dark:text-white">
                  {index + 1}. {place.name}
                </div>
                {place.address && (
                  <div className="text-gray-600 dark:text-gray-400 text-xs">
                    📍 {place.address}
                  </div>
                )}
                {place.rating && (
                  <div className="text-gray-600 dark:text-gray-400 text-xs">
                    ⭐ {place.rating} {place.user_ratings_total && `(${place.user_ratings_total} reviews)`}
                  </div>
                )}
              </div>
            ))}
            
            {mapsData.places.length > 3 && (
              <div className="text-xs text-gray-500 dark:text-gray-400">
                ... and {mapsData.places.length - 3} more places shown on map
              </div>
            )}
          </div>
        </div>
      )
    }

    if (mapsData.routes && mapsData.routes.length > 0) {
      const route = mapsData.routes[0]
      return (
        <div className="mt-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
          <div className="flex items-center space-x-2 mb-2">
            <MapPin className="w-4 h-4 text-green-600" />
            <span className="text-sm font-medium text-green-800 dark:text-green-200">
              Route Information
            </span>
          </div>
          
          <div className="text-sm space-y-1">
            <div className="font-medium text-gray-900 dark:text-white">
              {mapsData.origin} → {mapsData.destination}
            </div>
            <div className="text-gray-600 dark:text-gray-400">
              📏 {route.distance} • ⏱️ {route.duration}
            </div>
          </div>
        </div>
      )
    }

    return null
  }

  if (messages.length === 0) {
    return null
  }

  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div className={`flex max-w-4xl ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'} space-x-3`}>
            {/* Avatar */}
            <div className="flex-shrink-0">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                message.role === 'user' 
                  ? 'bg-primary-600 text-white' 
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
              }`}>
                {message.role === 'user' ? (
                  <User className="w-4 h-4" />
                ) : (
                  <Bot className="w-4 h-4" />
                )}
              </div>
            </div>

            {/* Message Content */}
            <div className="flex-1 min-w-0">
              <div className={`message-bubble ${
                message.role === 'user' ? 'message-user' : 'message-assistant'
              }`}>
                <div className="prose prose-sm max-w-none dark:prose-invert">
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                      a: ({ href, children }) => (
                        <a 
                          href={href} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-blue-600 dark:text-blue-400 hover:underline"
                        >
                          {children}
                        </a>
                      ),
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>

                {/* Maps data info */}
                {message.role === 'assistant' && renderMapsInfo(message.mapsData)}
              </div>

              {/* Timestamp */}
              <div className={`mt-1 text-xs text-gray-500 dark:text-gray-400 ${
                message.role === 'user' ? 'text-right' : 'text-left'
              }`}>
                <Clock className="w-3 h-3 inline mr-1" />
                {formatTimestamp(message.timestamp)}
              </div>
            </div>
          </div>
        </div>
      ))}
      
      <div ref={messagesEndRef} />
    </div>
  )
}

