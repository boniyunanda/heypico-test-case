'use client'

import { useState, useCallback } from 'react'
import { toast } from 'react-hot-toast'

interface GeolocationState {
  lat: number
  lng: number
}

export function useGeolocation() {
  const [location, setLocation] = useState<GeolocationState | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const requestLocation = useCallback(() => {
    if (!navigator.geolocation) {
      const errorMsg = 'Geolocation is not supported by this browser'
      setError(errorMsg)
      toast.error(errorMsg)
      return
    }

    setIsLoading(true)
    setError(null)

    const options: PositionOptions = {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 300000 // 5 minutes
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const newLocation = {
          lat: position.coords.latitude,
          lng: position.coords.longitude
        }
        
        setLocation(newLocation)
        setIsLoading(false)
        
        // Store in localStorage for persistence
        localStorage.setItem('userLocation', JSON.stringify(newLocation))
        
        toast.success('Location updated successfully')
      },
      (error) => {
        let errorMsg = 'Failed to get location'
        
        switch (error.code) {
          case error.PERMISSION_DENIED:
            errorMsg = 'Location access denied by user'
            break
          case error.POSITION_UNAVAILABLE:
            errorMsg = 'Location information unavailable'
            break
          case error.TIMEOUT:
            errorMsg = 'Location request timed out'
            break
          default:
            errorMsg = 'An unknown error occurred'
            break
        }
        
        setError(errorMsg)
        setIsLoading(false)
        toast.error(errorMsg)
      },
      options
    )
  }, [])

  // Load saved location on mount
  useState(() => {
    const savedLocation = localStorage.getItem('userLocation')
    if (savedLocation) {
      try {
        const parsed = JSON.parse(savedLocation)
        if (parsed.lat && parsed.lng) {
          setLocation(parsed)
        }
      } catch (e) {
        console.error('Failed to parse saved location:', e)
      }
    }
  })

  const clearLocation = useCallback(() => {
    setLocation(null)
    setError(null)
    localStorage.removeItem('userLocation')
    toast.success('Location cleared')
  }, [])

  return {
    location,
    isLoading,
    error,
    requestLocation,
    clearLocation,
    hasLocation: !!location
  }
}

