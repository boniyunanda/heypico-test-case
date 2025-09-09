'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Send, MapPin, Loader2 } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { useSocket } from '@/hooks/useSocket'
import { useGeolocation } from '@/hooks/useGeolocation'
import MessageList from './MessageList'
import GoogleMapDisplay from './GoogleMapDisplay'
import TypingIndicator from './TypingIndicator'

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: string
  mapsData?: any
}

interface ChatInterfaceProps {
  conversationId: string
}

export default function ChatInterface({ conversationId }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [currentMapsData, setCurrentMapsData] = useState(null)
  
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()
  
  // Custom hooks
  const { socket, isConnected } = useSocket()
  const { location: userLocation, requestLocation, isLoading: locationLoading } = useGeolocation()

  // Auto-scroll to bottom
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  // Socket event handlers
  useEffect(() => {
    if (!socket) return

    const handleMessage = (data: any) => {
      if (data.type === 'typing') {
        setIsTyping(true)
      } else if (data.type === 'complete') {
        setIsTyping(false)
        
        const assistantMessage: Message = {
          id: `msg_${Date.now()}`,
          content: data.message,
          role: 'assistant',
          timestamp: data.timestamp || new Date().toISOString(),
          mapsData: data.maps_data
        }
        
        setMessages(prev => [...prev, assistantMessage])
        setCurrentMapsData(data.maps_data)
      } else if (data.type === 'error') {
        setIsTyping(false)
        toast.error(data.message || 'An error occurred')
      }
    }

    socket.on('message', handleMessage)
    socket.on('typing', () => setIsTyping(true))
    socket.on('complete', handleMessage)
    socket.on('error', handleMessage)

    return () => {
      socket.off('message', handleMessage)
      socket.off('typing')
      socket.off('complete')
      socket.off('error')
    }
  }, [socket])

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: async (message: string) => {
      if (!socket || !isConnected) {
        throw new Error('Not connected to server')
      }

      // Add user message immediately
      const userMessage: Message = {
        id: `msg_${Date.now()}`,
        content: message,
        role: 'user',
        timestamp: new Date().toISOString()
      }
      
      setMessages(prev => [...prev, userMessage])
      setInputValue('')
      setIsTyping(true)

      // Send via WebSocket
      socket.emit('message', {
        message,
        conversation_id: conversationId,
        user_id: 'user_123', // In real app, get from auth
        location: userLocation
      })
    },
    onError: (error) => {
      setIsTyping(false)
      toast.error('Failed to send message')
      console.error('Send message error:', error)
    }
  })

  const handleSendMessage = async () => {
    const message = inputValue.trim()
    if (!message || sendMessageMutation.isPending) return

    try {
      await sendMessageMutation.mutateAsync(message)
    } catch (error) {
      console.error('Error sending message:', error)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleLocationRequest = () => {
    requestLocation()
    toast.success('Location requested')
  }

  // Example queries for quick testing
  const exampleQueries = [
    "Find coffee shops near Times Square, New York",
    "Show me restaurants within 2 miles of Central Park",
    "Get directions from Brooklyn Bridge to Statue of Liberty",
    "Where is the nearest gas station to JFK Airport?"
  ]

  return (
    <div className="flex h-full">
      {/* Chat Panel */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Connection Status */}
        <div className="px-4 py-2 bg-gray-100 dark:bg-gray-800 border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            
            <div className="flex items-center space-x-2">
              <button
                onClick={handleLocationRequest}
                disabled={locationLoading}
                className="flex items-center space-x-1 px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-md hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
              >
                {locationLoading ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <MapPin className="w-3 h-3" />
                )}
                <span>{userLocation ? 'Update Location' : 'Get Location'}</span>
              </button>
              
              {userLocation && (
                <span className="text-xs text-gray-500">
                  📍 {userLocation.lat.toFixed(4)}, {userLocation.lng.toFixed(4)}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 message-container scrollbar-thin">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                  Welcome to Local LLM with Maps! 🗺️
                </h2>
                <p className="text-gray-600 dark:text-gray-400">
                  Ask me about places to go, restaurants, directions, or any location-based questions.
                </p>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-4xl mx-auto">
                {exampleQueries.map((query, index) => (
                  <button
                    key={index}
                    onClick={() => setInputValue(query)}
                    className="p-3 text-left bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-primary-300 dark:hover:border-primary-600 transition-colors"
                  >
                    <div className="text-sm text-gray-900 dark:text-white">{query}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
          
          <MessageList messages={messages} />
          
          {isTyping && <TypingIndicator />}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 dark:border-gray-700 p-4">
          <div className="flex space-x-3">
            <div className="flex-1">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask about places, directions, or locations..."
                className="w-full resize-none rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-3 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:border-primary-500 focus:ring-1 focus:ring-primary-500 focus:outline-none"
                rows={inputValue.split('\n').length}
                maxLength={2000}
                disabled={sendMessageMutation.isPending || !isConnected}
              />
            </div>
            
            <button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || sendMessageMutation.isPending || !isConnected}
              className="flex items-center justify-center w-12 h-12 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
            >
              {sendMessageMutation.isPending ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
          
          <div className="mt-2 flex justify-between text-xs text-gray-500 dark:text-gray-400">
            <span>Press Enter to send, Shift+Enter for new line</span>
            <span>{inputValue.length}/2000</span>
          </div>
        </div>
      </div>

      {/* Maps Panel */}
      <div className="w-1/2 border-l border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
        <div className="h-full flex flex-col">
          <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <h3 className="font-semibold text-gray-900 dark:text-white">
              📍 Interactive Map
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {currentMapsData ? 'Showing search results' : 'Ask about locations to see results here'}
            </p>
          </div>
          
          <div className="flex-1">
            <GoogleMapDisplay 
              mapsData={currentMapsData}
              userLocation={userLocation}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

