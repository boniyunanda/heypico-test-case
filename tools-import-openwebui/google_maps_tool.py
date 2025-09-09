"""
title: Google Maps Search
author: Local LLM Maps Integration
author_url: https://github.com/your-repo
funding_url: https://github.com/sponsors/your-repo
version: 2.1.0
requirements: googlemaps, redis
"""

import os
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from pydantic import BaseModel, Field
import re

try:
    import googlemaps
    import redis
except ImportError as e:
    logging.error(f"Missing required dependencies: {e}")
    raise

log = logging.getLogger(__name__)


class Tools:
    class Valves(BaseModel):
        GOOGLE_MAPS_API_KEY: str = Field(
            default="", description="Google Maps API Key from Google Cloud Console"
        )
        ENABLE_CACHING: bool = Field(
            default=True, description="Enable Redis caching for better performance"
        )
        MAX_RESULTS: int = Field(
            default=10, description="Maximum number of results to return"
        )
        DEFAULT_RADIUS: int = Field(
            default=5000, description="Default search radius in meters"
        )

    def __init__(self):
        self.valves = self.Valves()
        self.rate_limiter = {}

    def search_places(
        self,
        query: str,
        location: Optional[str] = None,
        radius: Optional[int] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Search for places using Google Maps.
        
        Args:
            query (str): What to search for (e.g., "coffee shops", "restaurants", "gas stations")
            location (str, optional): Where to search (e.g., "Times Square", "40.7580,-73.9855", "New York")
            radius (int, optional): Search radius in meters (default: 5000)
        
        Returns:
            str: List of found places with addresses, ratings, and Google Maps links
        """
        return self._execute_search("search_places", query=query, location=location, radius=radius, __user__=__user__)

    def get_directions(
        self,
        origin: str,
        destination: str,
        travel_mode: Optional[str] = "driving",
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Get directions between two locations.
        
        Args:
            origin (str): Starting location (e.g., "Times Square", "40.7580,-73.9855")
            destination (str): Destination (e.g., "Central Park", "Brooklyn Bridge")
            travel_mode (str, optional): How to travel - "driving", "walking", "transit", or "bicycling"
        
        Returns:
            str: Turn-by-turn directions with distance and duration
        """
        return self._execute_search("get_directions", origin=origin, destination=destination, travel_mode=travel_mode, __user__=__user__)

    def find_address(
        self,
        address: str,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Find the coordinates and details for an address.
        
        Args:
            address (str): Address to find (e.g., "123 Main St, New York, NY")
        
        Returns:
            str: Address details with coordinates and Google Maps link
        """
        return self._execute_search("geocode", address=address, __user__=__user__)

    def nearby_places(
        self,
        latitude: float,
        longitude: float,
        place_type: str,
        radius: Optional[int] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Find places near specific coordinates.
        
        Args:
            latitude (float): Latitude coordinate
            longitude (float): Longitude coordinate  
            place_type (str): Type of place (e.g., "restaurant", "cafe", "gas_station")
            radius (int, optional): Search radius in meters (default: 5000)
        
        Returns:
            str: List of nearby places with details
        """
        location = f"{latitude},{longitude}"
        return self._execute_search("nearby_search", location=location, place_type=place_type, radius=radius, __user__=__user__)

    def _execute_search(self, action: str, **kwargs) -> str:
        """Internal function to execute Google Maps searches"""
        try:
            # Get API key
            api_key = self.valves.GOOGLE_MAPS_API_KEY or os.getenv("GOOGLE_MAPS_API_KEY")
            if not api_key or api_key in ["", "your-google-maps-api-key-here"]:
                return "❌ **Google Maps API key not configured**\n\nPlease set your API key in the tool's Valves configuration."
            
            # Initialize Google Maps client
            gmaps = googlemaps.Client(key=api_key)
            
            # Initialize Redis for caching (optional)
            redis_client = None
            if self.valves.ENABLE_CACHING:
                try:
                    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
                    redis_client = redis.from_url(redis_url, decode_responses=True, socket_timeout=2)
                    redis_client.ping()
                except Exception:
                    pass  # Continue without caching
            
            # Set defaults
            radius = kwargs.get('radius') or self.valves.DEFAULT_RADIUS
            
            # Generate cache key
            cache_key = self._generate_cache_key(action, kwargs)
            
            # Check cache
            if redis_client:
                try:
                    cached = redis_client.get(cache_key)
                    if cached:
                        return cached
                except Exception:
                    pass
            
            # Execute the search
            result = self._perform_search(gmaps, action, **kwargs)
            
            # Cache result
            if redis_client and not result.startswith("❌"):
                try:
                    redis_client.setex(cache_key, 300, result)  # 5 min cache
                except Exception:
                    pass
            
            return result
            
        except Exception as e:
            log.error(f"Search execution error: {e}")
            return f"❌ **Google Maps Error**: {str(e)}"

    def _perform_search(self, gmaps, action: str, **kwargs) -> str:
        """Perform the actual Google Maps API call"""
        try:
            if action == "search_places":
                return self._search_places_simple(gmaps, kwargs.get('query'), kwargs.get('location'), kwargs.get('radius', 5000))
            
            elif action == "nearby_search":
                return self._nearby_search_simple(gmaps, kwargs.get('location'), kwargs.get('place_type'), kwargs.get('radius', 5000))
            
            elif action == "get_directions":
                return self._get_directions_simple(gmaps, kwargs.get('origin'), kwargs.get('destination'), kwargs.get('travel_mode', 'driving'))
            
            elif action == "geocode":
                return self._geocode_simple(gmaps, kwargs.get('address'))
            
            else:
                return f"❌ **Unknown action**: {action}"
                
        except Exception as e:
            return f"❌ **API Error**: {str(e)}"

    def _search_places_simple(self, gmaps, query: str, location: str, radius: int) -> str:
        """Simple place search with text output"""
        try:
            # Prepare search parameters
            if location and "," in location:
                # Coordinates provided
                lat, lng = map(float, location.split(","))
                places_result = gmaps.places_nearby(
                    location=(lat, lng),
                    radius=radius,
                    keyword=query
                )
            else:
                # Text search
                search_query = f"{query} near {location}" if location else query
                places_result = gmaps.places(query=search_query)
            
            places = places_result.get("results", [])[:self.valves.MAX_RESULTS]
            
            if not places:
                return f"❌ **No results found** for '{query}'" + (f" near {location}" if location else "")
            
            # Format results
            result = f"🗺️ **Found {len(places)} places for '{query}'"
            if location:
                result += f" near {location}"
            result += ":**\n\n"
            
            for i, place in enumerate(places, 1):
                result += f"**{i}. {place.get('name', 'Unknown')}**\n"
                
                if place.get('formatted_address'):
                    result += f"   📍 {place['formatted_address']}\n"
                elif place.get('vicinity'):
                    result += f"   📍 {place['vicinity']}\n"
                
                if place.get('rating'):
                    result += f"   ⭐ {place['rating']}"
                    if place.get('user_ratings_total'):
                        result += f" ({place['user_ratings_total']} reviews)"
                    result += "\n"
                
                if place.get('price_level'):
                    result += f"   💰 {'$' * place['price_level']}\n"
                
                # Opening status
                if place.get('opening_hours', {}).get('open_now') is not None:
                    status = "🟢 Open Now" if place['opening_hours']['open_now'] else "🔴 Closed"
                    result += f"   {status}\n"
                
                # Google Maps link
                if place.get('place_id'):
                    result += f"   🔗 [Open in Google Maps](https://maps.google.com/maps/place/?q=place_id:{place['place_id']})\n"
                
                result += "\n"
            
            # Add embedded static map
            if places:
                center_lat = sum(p["geometry"]["location"]["lat"] for p in places) / len(places)
                center_lng = sum(p["geometry"]["location"]["lng"] for p in places) / len(places)
                
                # Create markers parameter for static map
                markers = "|".join([
                    f"color:red|{p['geometry']['location']['lat']},{p['geometry']['location']['lng']}"
                    for p in places[:10]
                ])
                
                api_key = self.valves.GOOGLE_MAPS_API_KEY or os.getenv("GOOGLE_MAPS_API_KEY")
                if api_key:
                    static_map_url = (
                        f"https://maps.googleapis.com/maps/api/staticmap?"
                        f"center={center_lat},{center_lng}&zoom=14&size=640x400&maptype=roadmap&"
                        f"markers={markers}&key={api_key}"
                    )
                    result += f"\n📍 **Map View:**\n![Coffee Shops Map]({static_map_url})\n"
                    result += f"\n🔗 [View Interactive Map](https://maps.google.com/maps/search/?api=1&query={query.replace(' ', '+')}+near+{location.replace(' ', '+') if location else 'me'})\n"
            
            return result
            
        except Exception as e:
            return f"❌ **Search failed**: {str(e)}"

    def _nearby_search_simple(self, gmaps, location: str, place_type: str, radius: int) -> str:
        """Simple nearby search"""
        try:
            if not location or "," not in location:
                return "❌ **Invalid location**: Please provide coordinates as 'latitude,longitude'"
            
            lat, lng = map(float, location.split(","))
            
            places_result = gmaps.places_nearby(
                location=(lat, lng),
                radius=radius,
                type=place_type
            )
            
            places = places_result.get("results", [])[:self.valves.MAX_RESULTS]
            
            if not places:
                return f"❌ **No {place_type} found** within {radius}m of {location}"
            
            result = f"🗺️ **Found {len(places)} {place_type} places near {location}:**\n\n"
            
            for i, place in enumerate(places, 1):
                result += f"**{i}. {place.get('name', 'Unknown')}**\n"
                if place.get('vicinity'):
                    result += f"   📍 {place['vicinity']}\n"
                if place.get('rating'):
                    result += f"   ⭐ {place['rating']}\n"
                if place.get('place_id'):
                    result += f"   🔗 [Open in Google Maps](https://maps.google.com/maps/place/?q=place_id:{place['place_id']})\n"
                result += "\n"
            
            return result
            
        except Exception as e:
            return f"❌ **Nearby search failed**: {str(e)}"

    def _get_directions_simple(self, gmaps, origin: str, destination: str, travel_mode: str) -> str:
        """Simple directions search"""
        try:
            directions_result = gmaps.directions(
                origin=origin,
                destination=destination,
                mode=travel_mode,
                units="metric"
            )
            
            if not directions_result:
                return f"❌ **No route found** from {origin} to {destination}"
            
            route = directions_result[0]
            leg = route["legs"][0]
            
            result = f"🧭 **Route from {origin} to {destination}**\n\n"
            result += f"**Distance**: {leg['distance']['text']} | **Duration**: {leg['duration']['text']}\n\n"
            result += "**Directions**:\n"
            
            for i, step in enumerate(leg["steps"][:10], 1):
                instruction = re.sub(r'<[^>]+>', '', step["html_instructions"])
                result += f"{i}. {instruction} ({step['distance']['text']})\n"
            
            if len(leg["steps"]) > 10:
                result += f"... and {len(leg['steps']) - 10} more steps\n"
            
            return result
            
        except Exception as e:
            return f"❌ **Directions failed**: {str(e)}"

    def _geocode_simple(self, gmaps, address: str) -> str:
        """Simple geocoding"""
        try:
            geocode_result = gmaps.geocode(address)
            
            if not geocode_result:
                return f"❌ **Address not found**: {address}"
            
            location = geocode_result[0]
            coords = location["geometry"]["location"]
            
            result = f"📍 **Location Found**\n\n"
            result += f"**Address**: {location['formatted_address']}\n"
            result += f"**Coordinates**: {coords['lat']}, {coords['lng']}\n"
            result += f"🔗 [Open in Google Maps](https://maps.google.com/maps/place/?q=place_id:{location['place_id']})\n"
            
            return result
            
        except Exception as e:
            return f"❌ **Geocoding failed**: {str(e)}"

    def _generate_cache_key(self, action: str, params: dict) -> str:
        """Generate cache key"""
        cache_params = {k: v for k, v in params.items() if v is not None and k != '__user__'}
        param_str = json.dumps({action: cache_params}, sort_keys=True)
        return f"maps:{hashlib.md5(param_str.encode()).hexdigest()[:12]}"
