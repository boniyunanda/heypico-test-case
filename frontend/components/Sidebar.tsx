'use client'

import { useState } from 'react'
import { X, Plus, MessageSquare, Map, Clock, Trash2 } from 'lucide-react'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
  currentConversation: string
  onNewConversation: () => void
}

export default function Sidebar({ 
  isOpen, 
  onClose, 
  currentConversation, 
  onNewConversation 
}: SidebarProps) {
  const [conversations] = useState([
    { id: 'conv_1', title: 'Coffee shops in NYC', timestamp: '2 hours ago' },
    { id: 'conv_2', title: 'Directions to Central Park', timestamp: '1 day ago' },
    { id: 'conv_3', title: 'Restaurants near Times Square', timestamp: '3 days ago' },
  ])

  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <div className={`
        fixed md:relative inset-y-0 left-0 z-50 w-80 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}>
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Conversations
            </h2>
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 md:hidden"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* New Conversation Button */}
          <div className="p-4">
            <button
              onClick={onNewConversation}
              className="w-full flex items-center space-x-2 px-4 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
            >
              <Plus className="w-5 h-5" />
              <span>New Conversation</span>
            </button>
          </div>

          {/* Conversation List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className={`p-3 rounded-lg cursor-pointer transition-colors group ${
                  conv.id === currentConversation
                    ? 'bg-primary-100 dark:bg-primary-900 border border-primary-200 dark:border-primary-800'
                    : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      <MessageSquare className="w-4 h-4 text-gray-400" />
                      <h3 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {conv.title}
                      </h3>
                    </div>
                    <div className="flex items-center space-x-1 text-xs text-gray-500 dark:text-gray-400">
                      <Clock className="w-3 h-3" />
                      <span>{conv.timestamp}</span>
                    </div>
                  </div>
                  
                  <button className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 dark:hover:bg-red-900 rounded transition-all">
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-gray-200 dark:border-gray-700">
            <div className="space-y-2 text-xs text-gray-500 dark:text-gray-400">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-500 rounded-full" />
                <span>LLM: Llama 3 (Local)</span>
              </div>
              <div className="flex items-center space-x-2">
                <Map className="w-3 h-3" />
                <span>Maps: Google Maps API</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-blue-500 rounded-full" />
                <span>Cache: Redis</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

