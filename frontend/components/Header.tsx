'use client'

import { Menu, MapPin, Settings, Github } from 'lucide-react'

interface HeaderProps {
  onMenuClick: () => void
  conversationId: string
}

export default function Header({ onMenuClick, conversationId }: HeaderProps) {
  return (
    <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-3">
      <div className="flex items-center justify-between">
        {/* Left side */}
        <div className="flex items-center space-x-4">
          <button
            onClick={onMenuClick}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors md:hidden"
          >
            <Menu className="w-5 h-5" />
          </button>
          
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <MapPin className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
                Local LLM Maps
              </h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                AI-Powered Location Search
              </p>
            </div>
          </div>
        </div>

        {/* Center - Conversation Info */}
        <div className="hidden md:block">
          <div className="text-center">
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              Current Conversation
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">
              {conversationId.slice(-8)}
            </p>
          </div>
        </div>

        {/* Right side */}
        <div className="flex items-center space-x-2">
          <a
            href="https://github.com/your-repo/local-llm-maps"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            title="View on GitHub"
          >
            <Github className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </a>
          
          <button
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            title="Settings"
          >
            <Settings className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </button>
        </div>
      </div>
    </header>
  )
}

