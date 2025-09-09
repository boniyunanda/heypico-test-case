'use client'

import { useCallback, useState, useEffect, useRef } from 'react'
import { GoogleMap, Marker, InfoWindow, useJsApiLoader } from '@react-google-maps/api'
import { MapPin, ExternalLink, Star, Clock, DollarSign } from 'lucide-react'

const libraries: ("places" | "geometry")[] = ["places", "geometry"]

const mapContainerStyle = {
  width: '100%',
  height: '100%'
}

const defaultCenter = {
  lat: 40.7128,
  lng: -74.0060 // New York City
}

const mapOptions = {
  disableDefaultUI: false,
  zoomControl: true,
  streetViewControl: true,
  mapTypeControl: true,
  fullscreenControl: true,
  styles: [
    {
      featureType: "poi.business",
      elementType: "labels",
      stylers: [{ visibility: "off" }]
    }
  ]
}

interface Place {
  name: string
  place_id: string
  address?: string
  location: { lat: number; lng: number }
  rating?: number
  user_ratings_total?: number
  price_level?: number
  types: string[]
  is_open?: boolean
  photo_reference?: string
  website?: string
  phone?: string
}

interface MapsData {
  places?: Place[]
  routes?: any[]
  map_center?: { lat: number; lng: number }
  search_query?: string
  total_results?: number
}

interface GoogleMapDisplayProps {
  mapsData?: MapsData | null
  userLocation?: { lat: number; lng: number } | null
}

export default function GoogleMapDisplay({ mapsData, userLocation }: GoogleMapDisplayProps) {
  const { isLoaded, loadError } = useJsApiLoader({
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '',
    libraries,
  })

  const [map, setMap] = useState<google.maps.Map | null>(null)
  const [selectedPlace, setSelectedPlace] = useState<Place | null>(null)
  const [markers, setMarkers] = useState<google.maps.Marker[]>([])
  
  const mapRef = useRef<google.maps.Map | null>(null)

  const onLoad = useCallback((map: google.maps.Map) => {
    setMap(map)
    mapRef.current = map
  }, [])

  const onUnmount = useCallback(() => {
    setMap(null)
    mapRef.current = null
  }, [])

  // Clear existing markers
  const clearMarkers = useCallback(() => {
    markers.forEach(marker => marker.setMap(null))
    setMarkers([])
  }, [markers])

  // Update map when mapsData changes
  useEffect(() => {
    if (!map || !isLoaded || !mapsData) return

    clearMarkers()

    if (mapsData.places && mapsData.places.length > 0) {
      const bounds = new google.maps.LatLngBounds()
      const newMarkers: google.maps.Marker[] = []

      mapsData.places.forEach((place, index) => {
        const marker = new google.maps.Marker({
          position: place.location,
          map: map,
          title: place.name,
          label: {
            text: String(index + 1),
            color: 'white',
            fontWeight: 'bold'
          },
          icon: {
            url: getMarkerIcon(place.types),
            scaledSize: new google.maps.Size(40, 40)
          }
        })

        marker.addListener('click', () => {
          setSelectedPlace(place)
        })

        newMarkers.push(marker)
        bounds.extend(place.location)
      })

      setMarkers(newMarkers)

      // Fit map to show all markers
      if (mapsData.places.length > 1) {
        map.fitBounds(bounds)
        
        // Ensure minimum zoom
        google.maps.event.addListenerOnce(map, 'bounds_changed', () => {
          if (map.getZoom()! > 16) {
            map.setZoom(16)
          }
        })
      } else {
        // Single place - center on it
        map.setCenter(mapsData.places[0].location)
        map.setZoom(15)
      }
    } else if (mapsData.map_center) {
      // Center on provided location
      map.setCenter(mapsData.map_center)
      map.setZoom(13)
    }
  }, [map, mapsData, isLoaded, clearMarkers])

  const getMarkerIcon = (types: string[]) => {
    const typeIconMap: { [key: string]: string } = {
      restaurant: "🍽️",
      cafe: "☕",
      gas_station: "⛽",
      hospital: "🏥",
      bank: "🏦",
      school: "🏫",
      store: "🏪",
      hotel: "🏨",
      pharmacy: "💊",
      atm: "🏧"
    }

    for (const type of types) {
      if (typeIconMap[type]) {
        return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(
          `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">
            <circle cx="20" cy="20" r="18" fill="#2563eb" stroke="white" stroke-width="2"/>
            <text x="20" y="26" text-anchor="middle" font-size="16">${typeIconMap[type]}</text>
          </svg>`
        )}`
      }
    }

    // Default marker
    return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(
      `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">
        <circle cx="20" cy="20" r="18" fill="#dc2626" stroke="white" stroke-width="2"/>
        <circle cx="20" cy="20" r="8" fill="white"/>
      </svg>`
    )}`
  }

  if (loadError) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-100 dark:bg-gray-800">
        <div className="text-center">
          <MapPin className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            Maps Loading Error
          </h3>
          <p className="text-gray-600 dark:text-gray-400 text-sm">
            Failed to load Google Maps. Please check your API key.
          </p>
        </div>
      </div>
    )
  }

  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-100 dark:bg-gray-800">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading Google Maps...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full relative">
      <GoogleMap
        mapContainerStyle={mapContainerStyle}
        center={mapsData?.map_center || userLocation || defaultCenter}
        zoom={mapsData?.places?.length ? 13 : 11}
        onLoad={onLoad}
        onUnmount={onUnmount}
        options={mapOptions}
      >
        {/* User location marker */}
        {userLocation && (
          <Marker
            position={userLocation}
            title="Your Location"
            icon={{
              url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(
                `<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 30 30">
                  <circle cx="15" cy="15" r="12" fill="#3b82f6" stroke="white" stroke-width="3"/>
                  <circle cx="15" cy="15" r="4" fill="white"/>
                </svg>`
              )}`,
              scaledSize: new google.maps.Size(30, 30)
            }}
          />
        )}

        {/* Info Window */}
        {selectedPlace && (
          <InfoWindow
            position={selectedPlace.location}
            onCloseClick={() => setSelectedPlace(null)}
          >
            <div className="p-3 max-w-sm">
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-bold text-lg text-gray-900">{selectedPlace.name}</h3>
              </div>
              
              {selectedPlace.address && (
                <p className="text-gray-600 text-sm mb-2">{selectedPlace.address}</p>
              )}
              
              <div className="space-y-2">
                {selectedPlace.rating && (
                  <div className="flex items-center space-x-1">
                    <Star className="w-4 h-4 text-yellow-500 fill-current" />
                    <span className="text-sm font-medium">{selectedPlace.rating}</span>
                    {selectedPlace.user_ratings_total && (
                      <span className="text-sm text-gray-500">({selectedPlace.user_ratings_total})</span>
                    )}
                  </div>
                )}
                
                {selectedPlace.price_level && (
                  <div className="flex items-center space-x-1">
                    <DollarSign className="w-4 h-4 text-green-600" />
                    <span className="text-sm">{'$'.repeat(selectedPlace.price_level)}</span>
                  </div>
                )}
                
                {selectedPlace.is_open !== undefined && (
                  <div className="flex items-center space-x-1">
                    <Clock className="w-4 h-4 text-gray-500" />
                    <span className={`text-sm ${selectedPlace.is_open ? 'text-green-600' : 'text-red-600'}`}>
                      {selectedPlace.is_open ? 'Open Now' : 'Closed'}
                    </span>
                  </div>
                )}
              </div>
              
              <div className="mt-3 space-y-2">
                <a
                  href={`https://maps.google.com/maps/place/?q=place_id:${selectedPlace.place_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center space-x-1 text-blue-600 hover:text-blue-800 text-sm"
                >
                  <ExternalLink className="w-4 h-4" />
                  <span>View on Google Maps</span>
                </a>
                
                <br />
                
                <a
                  href={`https://maps.google.com/maps/dir/?api=1&destination=place_id:${selectedPlace.place_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center space-x-1 text-blue-600 hover:text-blue-800 text-sm"
                >
                  <MapPin className="w-4 h-4" />
                  <span>Get Directions</span>
                </a>
              </div>
            </div>
          </InfoWindow>
        )}
      </GoogleMap>

      {/* Map overlay info */}
      {mapsData?.places && (
        <div className="absolute top-4 left-4 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-3 max-w-xs">
          <h4 className="font-semibold text-gray-900 dark:text-white mb-1">
            Search Results
          </h4>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {mapsData.total_results} places found
            {mapsData.search_query && (
              <span> for "{mapsData.search_query}"</span>
            )}
          </p>
        </div>
      )}

      {/* No data state */}
      {!mapsData && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100 dark:bg-gray-800">
          <div className="text-center">
            <MapPin className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              Ready for Location Queries
            </h3>
            <p className="text-gray-600 dark:text-gray-400 text-sm max-w-xs">
              Ask about places, restaurants, directions, or any location-based questions to see results here.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

