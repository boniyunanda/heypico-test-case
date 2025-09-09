<!--
Google Maps Display Component for Open WebUI
Displays places and directions in the chat interface
-->

<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { Loader } from '@googlemaps/js-api-loader';
  
  // Props
  export let data: {
    type?: string;
    places?: any[];
    routes?: any[];
    map_center?: { lat: number; lng: number };
    origin?: string;
    destination?: string;
    search_query?: string;
    action?: string;
  };
  
  // Component state
  let mapElement: HTMLElement;
  let map: google.maps.Map;
  let markers: google.maps.Marker[] = [];
  let infoWindows: google.maps.InfoWindow[] = [];
  let directionsRenderer: google.maps.DirectionsRenderer;
  let isLoading = true;
  let error: string | null = null;
  
  // Google Maps loader
  const loader = new Loader({
    apiKey: import.meta.env.VITE_PUBLIC_GOOGLE_MAPS_KEY || '',
    version: "weekly",
    libraries: ["places", "geometry"]
  });
  
  onMount(async () => {
    try {
      await initializeMap();
    } catch (err) {
      console.error("Error initializing map:", err);
      error = "Failed to load map. Please check your internet connection.";
      isLoading = false;
    }
  });
  
  async function initializeMap() {
    try {
      // Load Google Maps libraries
      const { Map } = await loader.importLibrary("maps") as google.maps.MapsLibrary;
      const { Marker } = await loader.importLibrary("marker") as google.maps.MarkerLibrary;
      const { InfoWindow } = await loader.importLibrary("maps") as google.maps.MapsLibrary;
      
      // Determine map center
      const center = getMapCenter();
      
      // Initialize map
      map = new Map(mapElement, {
        center: center,
        zoom: getInitialZoom(),
        styles: getMapStyles(),
        mapTypeControl: true,
        streetViewControl: true,
        fullscreenControl: true,
        zoomControl: true
      });
      
      // Handle different data types
      if (data.places && data.places.length > 0) {
        await displayPlaces();
      }
      
      if (data.routes && data.routes.length > 0) {
        await displayDirections();
      }
      
      isLoading = false;
      
    } catch (err) {
      console.error("Map initialization error:", err);
      error = "Failed to initialize map";
      isLoading = false;
    }
  }
  
  function getMapCenter(): google.maps.LatLngLiteral {
    // Priority: explicit center > first place > default (NYC)
    if (data.map_center) {
      return data.map_center;
    }
    
    if (data.places && data.places.length > 0) {
      return data.places[0].location;
    }
    
    // Default to New York City
    return { lat: 40.7128, lng: -74.0060 };
  }
  
  function getInitialZoom(): number {
    if (data.places && data.places.length > 1) {
      return 12; // Show multiple places
    }
    
    if (data.routes && data.routes.length > 0) {
      return 10; // Show route overview
    }
    
    return 14; // Single place or default
  }
  
  function getMapStyles(): google.maps.MapTypeStyle[] {
    return [
      {
        featureType: "poi.business",
        elementType: "labels",
        stylers: [{ visibility: "off" }]
      },
      {
        featureType: "transit.station",
        elementType: "labels",
        stylers: [{ visibility: "off" }]
      }
    ];
  }
  
  async function displayPlaces() {
    if (!data.places || data.places.length === 0) return;
    
    const bounds = new google.maps.LatLngBounds();
    
    // Create markers for each place
    for (let i = 0; i < data.places.length; i++) {
      const place = data.places[i];
      
      // Create marker
      const marker = new google.maps.Marker({
        position: place.location,
        map: map,
        title: place.name,
        label: {
          text: String(i + 1),
          color: "white",
          fontWeight: "bold"
        },
        icon: {
          url: getMarkerIcon(place.types),
          scaledSize: new google.maps.Size(40, 40)
        }
      });
      
      // Create info window
      const infoWindow = new google.maps.InfoWindow({
        content: createInfoWindowContent(place, i + 1)
      });
      
      // Add click listener
      marker.addListener("click", () => {
        // Close other info windows
        infoWindows.forEach(iw => iw.close());
        infoWindow.open(map, marker);
      });
      
      markers.push(marker);
      infoWindows.push(infoWindow);
      bounds.extend(place.location);
    }
    
    // Fit map to show all markers
    if (data.places.length > 1) {
      map.fitBounds(bounds);
      
      // Ensure minimum zoom level
      google.maps.event.addListenerOnce(map, 'bounds_changed', () => {
        if (map.getZoom() > 16) {
          map.setZoom(16);
        }
      });
    }
  }
  
  async function displayDirections() {
    if (!data.routes || data.routes.length === 0) return;
    
    const { DirectionsRenderer } = await loader.importLibrary("maps") as google.maps.MapsLibrary;
    
    directionsRenderer = new DirectionsRenderer({
      map: map,
      polylineOptions: {
        strokeColor: "#4285F4",
        strokeOpacity: 0.8,
        strokeWeight: 6
      },
      suppressMarkers: false
    });
    
    // Use the first route
    const route = data.routes[0];
    
    // Create a directions result object
    const directionsResult = {
      routes: [{
        overview_path: google.maps.geometry.encoding.decodePath(route.polyline),
        legs: [{
          start_address: route.start_address,
          end_address: route.end_address,
          distance: { text: route.distance },
          duration: { text: route.duration },
          steps: route.steps || []
        }]
      }]
    };
    
    directionsRenderer.setDirections(directionsResult as google.maps.DirectionsResult);
  }
  
  function getMarkerIcon(types: string[] = []): string {
    // Return appropriate marker icon based on place type
    const typeIconMap: { [key: string]: string } = {
      restaurant: "🍽️",
      cafe: "☕",
      gas_station: "⛽",
      hospital: "🏥",
      bank: "🏦",
      school: "🏫",
      store: "🏪",
      hotel: "🏨"
    };
    
    for (const type of types) {
      if (typeIconMap[type]) {
        return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(
          `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">
            <circle cx="20" cy="20" r="18" fill="#4285F4" stroke="white" stroke-width="2"/>
            <text x="20" y="26" text-anchor="middle" font-size="16">${typeIconMap[type]}</text>
          </svg>`
        )}`;
      }
    }
    
    // Default marker
    return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(
      `<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">
        <circle cx="20" cy="20" r="18" fill="#EA4335" stroke="white" stroke-width="2"/>
        <circle cx="20" cy="20" r="8" fill="white"/>
      </svg>`
    )}`;
  }
  
  function createInfoWindowContent(place: any, index: number): string {
    const rating = place.rating ? `
      <div class="flex items-center mt-1">
        <span class="text-yellow-500">★</span>
        <span class="ml-1 text-sm">${place.rating}</span>
        ${place.user_ratings_total ? `<span class="ml-1 text-xs text-gray-500">(${place.user_ratings_total})</span>` : ''}
      </div>
    ` : '';
    
    const priceLevel = place.price_level ? `
      <div class="text-sm text-gray-600 mt-1">
        Price: ${'$'.repeat(place.price_level)}
      </div>
    ` : '';
    
    const openStatus = place.is_open !== undefined ? `
      <div class="text-sm mt-1">
        <span class="px-2 py-1 rounded text-xs ${place.is_open ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
          ${place.is_open ? 'Open' : 'Closed'}
        </span>
      </div>
    ` : '';
    
    return `
      <div class="p-3 max-w-xs">
        <div class="flex items-start gap-2">
          <span class="bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold">${index}</span>
          <div class="flex-1">
            <h3 class="font-semibold text-lg leading-tight">${place.name}</h3>
            ${place.address ? `<p class="text-sm text-gray-600 mt-1">${place.address}</p>` : ''}
            ${rating}
            ${priceLevel}
            ${openStatus}
            <div class="mt-3 space-y-1">
              <a href="https://www.google.com/maps/place/?q=place_id:${place.place_id}" 
                 target="_blank" 
                 rel="noopener noreferrer"
                 class="inline-block text-blue-600 text-sm hover:underline">
                📍 View on Google Maps
              </a>
              <br>
              <a href="https://www.google.com/maps/dir/?api=1&destination=place_id:${place.place_id}" 
                 target="_blank" 
                 rel="noopener noreferrer"
                 class="inline-block text-blue-600 text-sm hover:underline">
                🧭 Get Directions
              </a>
            </div>
          </div>
        </div>
      </div>
    `;
  }
  
  function handleRetry() {
    error = null;
    isLoading = true;
    initializeMap();
  }
  
  onDestroy(() => {
    // Clean up markers and info windows
    markers.forEach(marker => marker.setMap(null));
    infoWindows.forEach(infoWindow => infoWindow.close());
    
    if (directionsRenderer) {
      directionsRenderer.setMap(null);
    }
  });
</script>

<div class="w-full rounded-lg overflow-hidden shadow-lg my-4 bg-white dark:bg-gray-900">
  <!-- Header -->
  <div class="bg-gray-100 dark:bg-gray-800 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
    <div class="flex items-center justify-between">
      <h3 class="text-sm font-semibold flex items-center gap-2 text-gray-800 dark:text-gray-200">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd" />
        </svg>
        {#if data.action === 'search_places'}
          Search Results: {data.search_query || 'Places'}
        {:else if data.action === 'nearby_search'}
          Nearby Places
        {:else if data.action === 'get_directions'}
          Directions: {data.origin} → {data.destination}
        {:else if data.action === 'geocode'}
          Location Found
        {:else}
          Map View
        {/if}
      </h3>
      
      {#if data.places}
        <span class="text-xs text-gray-500 dark:text-gray-400">
          {data.places.length} result{data.places.length !== 1 ? 's' : ''}
        </span>
      {/if}
    </div>
  </div>
  
  <!-- Map Container -->
  <div class="relative">
    {#if isLoading}
      <div class="w-full h-96 flex items-center justify-center bg-gray-50 dark:bg-gray-800">
        <div class="text-center">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">Loading map...</p>
        </div>
      </div>
    {:else if error}
      <div class="w-full h-96 flex items-center justify-center bg-gray-50 dark:bg-gray-800">
        <div class="text-center">
          <svg class="w-12 h-12 text-red-500 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p class="text-sm text-red-600 dark:text-red-400 mb-2">{error}</p>
          <button 
            on:click={handleRetry}
            class="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    {:else}
      <div bind:this={mapElement} class="w-full h-96"></div>
    {/if}
  </div>
  
  <!-- Places List -->
  {#if data.places && data.places.length > 0}
    <div class="bg-white dark:bg-gray-900 p-4 max-h-64 overflow-y-auto border-t border-gray-200 dark:border-gray-700">
      <h4 class="text-sm font-semibold mb-3 text-gray-800 dark:text-gray-200">Places Found:</h4>
      <div class="space-y-3">
        {#each data.places as place, index}
          <div class="flex items-start gap-3 p-2 rounded hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
            <span class="flex-shrink-0 bg-blue-600 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold">
              {index + 1}
            </span>
            <div class="flex-1 min-w-0">
              <p class="font-medium text-sm text-gray-900 dark:text-gray-100 truncate">{place.name}</p>
              {#if place.address}
                <p class="text-xs text-gray-600 dark:text-gray-400 mt-1">{place.address}</p>
              {/if}
              <div class="flex items-center gap-4 mt-2">
                {#if place.rating}
                  <div class="flex items-center text-xs">
                    <span class="text-yellow-500">★</span>
                    <span class="ml-1 text-gray-600 dark:text-gray-400">{place.rating}</span>
                  </div>
                {/if}
                {#if place.price_level}
                  <span class="text-xs text-gray-600 dark:text-gray-400">
                    {'$'.repeat(place.price_level)}
                  </span>
                {/if}
                {#if place.is_open !== undefined}
                  <span class="px-2 py-0.5 rounded text-xs {place.is_open ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'}">
                    {place.is_open ? 'Open' : 'Closed'}
                  </span>
                {/if}
              </div>
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}
  
  <!-- Route Information -->
  {#if data.routes && data.routes.length > 0}
    <div class="bg-white dark:bg-gray-900 p-4 border-t border-gray-200 dark:border-gray-700">
      {#each data.routes as route, index}
        <div class="mb-4 last:mb-0">
          <div class="flex justify-between items-center mb-2">
            <span class="font-semibold text-sm text-gray-800 dark:text-gray-200">
              Route {index + 1}: {route.summary || 'Route'}
            </span>
            <div class="text-sm text-gray-600 dark:text-gray-400">
              <span class="font-medium">{route.distance}</span> · 
              <span class="font-medium">{route.duration}</span>
            </div>
          </div>
          
          {#if route.steps && route.steps.length > 0}
            <div class="text-xs text-gray-600 dark:text-gray-400 space-y-1">
              <p class="font-medium">Key directions:</p>
              {#each route.steps.slice(0, 3) as step}
                <p>• {step.instruction} ({step.distance})</p>
              {/each}
              {#if route.steps.length > 3}
                <p class="italic">... and {route.steps.length - 3} more steps</p>
              {/if}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  /* Ensure Google Maps displays properly */
  :global(.gm-style img) {
    max-width: none !important;
  }
  
  :global(.gm-style-iw) {
    font-family: inherit !important;
  }
  
  /* Custom scrollbar for places list */
  .overflow-y-auto {
    scrollbar-width: thin;
    scrollbar-color: #cbd5e0 #f7fafc;
  }
  
  .overflow-y-auto::-webkit-scrollbar {
    width: 6px;
  }
  
  .overflow-y-auto::-webkit-scrollbar-track {
    background: #f7fafc;
  }
  
  .overflow-y-auto::-webkit-scrollbar-thumb {
    background-color: #cbd5e0;
    border-radius: 3px;
  }
  
  .dark .overflow-y-auto {
    scrollbar-color: #4a5568 #2d3748;
  }
  
  .dark .overflow-y-auto::-webkit-scrollbar-track {
    background: #2d3748;
  }
  
  .dark .overflow-y-auto::-webkit-scrollbar-thumb {
    background-color: #4a5568;
  }
</style>
