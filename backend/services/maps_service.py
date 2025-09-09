"""
Google Maps Service
Handles all Google Maps API interactions with caching and error handling
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import googlemaps
from googlemaps.exceptions import ApiError, TransportError, Timeout

from services.cache_service import CacheService
from models import Place, Location, Route

logger = logging.getLogger(__name__)


class GoogleMapsService:
    """Google Maps API service with caching and error handling"""
    
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
        self._client = None
        self._api_key = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Google Maps client"""
        try:
            self._api_key = os.getenv("GOOGLE_MAPS_API_KEY")
            if not self._api_key or self._api_key == "your-google-maps-api-key-here":
                logger.error("Google Maps API key not configured")
                return
            
            self._client = googlemaps.Client(
                key=self._api_key,
                queries_per_second=10,
                retry_timeout=60
            )
            logger.info("✅ Google Maps client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Maps client: {e}")
    
    async def health_check(self) -> bool:
        """Check if Google Maps API is accessible"""
        try:
            if not self._client:
                return False
            
            # Test with a simple geocoding request
            result = await asyncio.to_thread(
                self._client.geocode, "New York, NY"
            )
            return bool(result)
            
        except Exception as e:
            logger.error(f"Google Maps health check failed: {e}")
            return False
    
    async def search_places(
        self,
        query: str,
        location: Optional[str] = None,
        radius: int = 5000,
        place_type: Optional[str] = None,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Search for places using Google Maps Places API
        """
        try:
            if not self._client:
                raise Exception("Google Maps client not initialized")
            
            # Generate cache key
            cache_key = f"places:{hash((query, location, radius, place_type, max_results))}"
            
            # Check cache
            cached = await self.cache_service.get(cache_key)
            if cached:
                logger.info("Returning cached places result")
                return cached
            
            # Prepare search parameters
            search_params = {"query": query}
            
            # Handle location parameter
            if location:
                if self._is_coordinates(location):
                    lat, lng = map(float, location.split(","))
                    search_params["location"] = (lat, lng)
                    search_params["radius"] = radius
                else:
                    search_params["query"] = f"{query} near {location}"
            
            # Execute search
            places_result = await asyncio.to_thread(
                self._client.places, **search_params
            )
            
            # Transform results
            places = self._transform_places(places_result.get("results", [])[:max_results])
            
            # Calculate map center
            map_center = None
            if places:
                avg_lat = sum(p["location"]["lat"] for p in places) / len(places)
                avg_lng = sum(p["location"]["lng"] for p in places) / len(places)
                map_center = {"lat": avg_lat, "lng": avg_lng}
            
            result = {
                "places": places,
                "total_results": len(places),
                "search_query": query,
                "location": location,
                "map_center": map_center,
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache result
            await self.cache_service.set(cache_key, result, ttl=300)
            
            return result
            
        except (ApiError, TransportError, Timeout) as e:
            logger.error(f"Google Maps API error: {e}")
            raise Exception(f"Google Maps API error: {str(e)}")
        except Exception as e:
            logger.error(f"Places search error: {e}")
            raise
    
    async def nearby_search(
        self,
        latitude: float,
        longitude: float,
        place_type: str,
        radius: int = 5000,
        keyword: Optional[str] = None,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Search for nearby places using coordinates
        """
        try:
            if not self._client:
                raise Exception("Google Maps client not initialized")
            
            # Generate cache key
            cache_key = f"nearby:{hash((latitude, longitude, place_type, radius, keyword, max_results))}"
            
            # Check cache
            cached = await self.cache_service.get(cache_key)
            if cached:
                return cached
            
            # Search parameters
            search_params = {
                "location": (latitude, longitude),
                "radius": radius,
                "type": place_type
            }
            
            if keyword:
                search_params["keyword"] = keyword
            
            # Execute search
            places_result = await asyncio.to_thread(
                self._client.places_nearby, **search_params
            )
            
            # Transform results
            places = self._transform_places(places_result.get("results", [])[:max_results])
            
            result = {
                "places": places,
                "total_results": len(places),
                "place_type": place_type,
                "center_location": {"lat": latitude, "lng": longitude},
                "radius": radius,
                "keyword": keyword,
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache result
            await self.cache_service.set(cache_key, result, ttl=300)
            
            return result
            
        except Exception as e:
            logger.error(f"Nearby search error: {e}")
            raise
    
    async def get_directions(
        self,
        origin: str,
        destination: str,
        travel_mode: str = "driving"
    ) -> Dict[str, Any]:
        """
        Get directions between two points
        """
        try:
            if not self._client:
                raise Exception("Google Maps client not initialized")
            
            # Generate cache key
            cache_key = f"directions:{hash((origin, destination, travel_mode))}"
            
            # Check cache
            cached = await self.cache_service.get(cache_key)
            if cached:
                return cached
            
            # Get directions
            directions_result = await asyncio.to_thread(
                self._client.directions,
                origin=origin,
                destination=destination,
                mode=travel_mode,
                alternatives=True,
                units="metric"
            )
            
            if not directions_result:
                raise Exception("No routes found")
            
            # Transform routes
            routes = []
            for route in directions_result[:3]:  # Max 3 routes
                leg = route["legs"][0]
                
                route_data = {
                    "summary": route.get("summary", "Route"),
                    "distance": leg["distance"]["text"],
                    "duration": leg["duration"]["text"],
                    "start_address": leg["start_address"],
                    "end_address": leg["end_address"],
                    "steps": [
                        {
                            "instruction": self._clean_html(step["html_instructions"]),
                            "distance": step["distance"]["text"],
                            "duration": step["duration"]["text"],
                            "maneuver": step.get("maneuver", "")
                        }
                        for step in leg["steps"]
                    ],
                    "polyline": route["overview_polyline"]["points"]
                }
                routes.append(route_data)
            
            result = {
                "routes": routes,
                "origin": origin,
                "destination": destination,
                "travel_mode": travel_mode,
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache result
            await self.cache_service.set(cache_key, result, ttl=600)  # 10 min cache
            
            return result
            
        except Exception as e:
            logger.error(f"Directions error: {e}")
            raise
    
    async def geocode_address(self, address: str) -> Dict[str, Any]:
        """
        Geocode an address to coordinates
        """
        try:
            if not self._client:
                raise Exception("Google Maps client not initialized")
            
            # Generate cache key
            cache_key = f"geocode:{hash(address)}"
            
            # Check cache
            cached = await self.cache_service.get(cache_key)
            if cached:
                return cached
            
            # Geocode
            geocode_result = await asyncio.to_thread(
                self._client.geocode, address
            )
            
            if not geocode_result:
                raise Exception(f"Address not found: {address}")
            
            location_data = geocode_result[0]
            coords = location_data["geometry"]["location"]
            
            result = {
                "formatted_address": location_data["formatted_address"],
                "location": {
                    "lat": coords["lat"],
                    "lng": coords["lng"]
                },
                "place_id": location_data["place_id"],
                "types": location_data.get("types", []),
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache result
            await self.cache_service.set(cache_key, result, ttl=3600)  # 1 hour cache
            
            return result
            
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            raise
    
    def _transform_places(self, places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform Google Maps places to our format"""
        transformed = []
        
        for place in places:
            try:
                place_data = {
                    "name": place.get("name", "Unknown"),
                    "place_id": place.get("place_id", ""),
                    "address": place.get("formatted_address") or place.get("vicinity", ""),
                    "location": {
                        "lat": place["geometry"]["location"]["lat"],
                        "lng": place["geometry"]["location"]["lng"]
                    },
                    "rating": place.get("rating"),
                    "user_ratings_total": place.get("user_ratings_total"),
                    "price_level": place.get("price_level"),
                    "types": place.get("types", []),
                    "business_status": place.get("business_status")
                }
                
                # Opening hours
                if "opening_hours" in place:
                    place_data["is_open"] = place["opening_hours"].get("open_now")
                
                # Photos
                if "photos" in place and place["photos"]:
                    place_data["photo_reference"] = place["photos"][0]["photo_reference"]
                
                # Additional details
                if "formatted_phone_number" in place:
                    place_data["phone"] = place["formatted_phone_number"]
                
                if "website" in place:
                    place_data["website"] = place["website"]
                
                transformed.append(place_data)
                
            except Exception as e:
                logger.warning(f"Failed to transform place: {e}")
                continue
        
        return transformed
    
    def _is_coordinates(self, location_str: str) -> bool:
        """Check if string is coordinates (lat,lng)"""
        try:
            if "," not in location_str:
                return False
            parts = location_str.split(",")
            if len(parts) != 2:
                return False
            lat, lng = map(float, parts)
            return -90 <= lat <= 90 and -180 <= lng <= 180
        except (ValueError, TypeError):
            return False
    
    def _clean_html(self, html_text: str) -> str:
        """Remove HTML tags from text"""
        import re
        if not html_text:
            return ""
        clean = re.compile('<.*?>')
        text = re.sub(clean, '', html_text)
        return re.sub(r'\s+', ' ', text).strip()
    
    async def get_place_photo_url(self, photo_reference: str, max_width: int = 400) -> str:
        """Get photo URL for a place"""
        if not self._api_key:
            return ""
        
        return (
            f"https://maps.googleapis.com/maps/api/place/photo?"
            f"maxwidth={max_width}&photo_reference={photo_reference}&key={self._api_key}"
        )

