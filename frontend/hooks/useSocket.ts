'use client'

import { useEffect, useState, useRef } from 'react'
import { io, Socket } from 'socket.io-client'
import { toast } from 'react-hot-toast'

export function useSocket() {
  const [socket, setSocket] = useState<Socket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 5

  useEffect(() => {
    const socketUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'
    
    const newSocket = io(socketUrl, {
      transports: ['websocket', 'polling'],
      timeout: 20000,
      forceNew: true,
    })

    // Connection event handlers
    newSocket.on('connect', () => {
      console.log('✅ Connected to server')
      setIsConnected(true)
      reconnectAttempts.current = 0
      toast.success('Connected to server')
    })

    newSocket.on('disconnect', (reason) => {
      console.log('❌ Disconnected from server:', reason)
      setIsConnected(false)
      
      if (reason === 'io server disconnect') {
        // Server disconnected, try to reconnect
        newSocket.connect()
      }
    })

    newSocket.on('connect_error', (error) => {
      console.error('Connection error:', error)
      setIsConnected(false)
      
      reconnectAttempts.current += 1
      
      if (reconnectAttempts.current <= maxReconnectAttempts) {
        toast.error(`Connection failed. Retrying... (${reconnectAttempts.current}/${maxReconnectAttempts})`)
        
        // Retry with exponential backoff
        setTimeout(() => {
          newSocket.connect()
        }, Math.pow(2, reconnectAttempts.current) * 1000)
      } else {
        toast.error('Failed to connect to server. Please refresh the page.')
      }
    })

    newSocket.on('reconnect', () => {
      console.log('🔄 Reconnected to server')
      toast.success('Reconnected to server')
      reconnectAttempts.current = 0
    })

    setSocket(newSocket)

    // Cleanup
    return () => {
      newSocket.close()
    }
  }, [])

  return { socket, isConnected }
}

