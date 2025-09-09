'use client'

import { useState, useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import ChatInterface from '@/components/ChatInterface'
import GoogleMapsProvider from '@/components/GoogleMapsProvider'
import Header from '@/components/Header'
import Sidebar from '@/components/Sidebar'

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
})

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [currentConversation, setCurrentConversation] = useState<string>('')

  useEffect(() => {
    // Generate initial conversation ID
    setCurrentConversation(`conv_${Date.now()}`)
  }, [])

  return (
    <QueryClientProvider client={queryClient}>
      <GoogleMapsProvider>
        <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
          {/* Sidebar */}
          <Sidebar 
            isOpen={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
            currentConversation={currentConversation}
            onNewConversation={() => setCurrentConversation(`conv_${Date.now()}`)}
          />
          
          {/* Main content */}
          <div className="flex-1 flex flex-col min-w-0">
            {/* Header */}
            <Header 
              onMenuClick={() => setSidebarOpen(!sidebarOpen)}
              conversationId={currentConversation}
            />
            
            {/* Chat Interface */}
            <main className="flex-1 overflow-hidden">
              <ChatInterface 
                conversationId={currentConversation}
              />
            </main>
          </div>
        </div>
        
        {/* Toast notifications */}
        <Toaster 
          position="top-right"
          toastOptions={{
            duration: 4000,
            className: 'text-sm',
          }}
        />
      </GoogleMapsProvider>
    </QueryClientProvider>
  )
}

