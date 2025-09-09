'use client'

import { Bot } from 'lucide-react'

export default function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex space-x-3 max-w-4xl">
        {/* Avatar */}
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full flex items-center justify-center bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
            <Bot className="w-4 h-4" />
          </div>
        </div>

        {/* Typing animation */}
        <div className="message-bubble message-assistant">
          <div className="flex items-center space-x-1">
            <span className="text-gray-500 dark:text-gray-400 text-sm">AI is thinking</span>
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

