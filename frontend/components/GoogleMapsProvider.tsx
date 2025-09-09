'use client'

import { createContext, useContext, ReactNode } from 'react'

interface GoogleMapsContextType {
  apiKey: string | undefined
  isLoaded: boolean
}

const GoogleMapsContext = createContext<GoogleMapsContextType>({
  apiKey: undefined,
  isLoaded: false
})

export function useGoogleMaps() {
  const context = useContext(GoogleMapsContext)
  if (!context) {
    throw new Error('useGoogleMaps must be used within GoogleMapsProvider')
  }
  return context
}

interface GoogleMapsProviderProps {
  children: ReactNode
}

export default function GoogleMapsProvider({ children }: GoogleMapsProviderProps) {
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY

  const value = {
    apiKey,
    isLoaded: !!apiKey
  }

  return (
    <GoogleMapsContext.Provider value={value}>
      {children}
    </GoogleMapsContext.Provider>
  )
}

