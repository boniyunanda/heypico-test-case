"""
Google Maps Function for Open WebUI
Provides place search, directions, and geocoding capabilities
"""

import os
import json
import hashlib
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import logging

try:
    import googlemaps
    import redis
    from cryptography.fernet import Fernet
except ImportError as e:
    logging.error(f"Missing required dependencies: {e}")
    raise

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleMapsFunction:
    """Google Maps integration function for Open WebUI"""
    
    def __init__(self):
        self.id = "google_maps"
        self.name = "Google Maps Search"
        self.description = "Search places, get directions, and geocode addresses using Google Maps"
        self.version = "1.0.0"
        
        # Initialize Google Maps client with error handling
        try:
            api_key = self._get_secure_api_key()
            if not api_key:
                raise ValueError("Google Maps API key not found")
                
            self.gmaps = googlemaps.Client(
                key=api_key,
                queries_per_second=10,
                retry_timeout=60
            )
        except Exception as e:
            logger.error(f"Failed to initialize Google Maps client: {e}")
            raise
        
        # Initialize Redis for caching
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed, caching disabled: {e}")
            self.redis_client = None
        
        # Rate limiting storage
        self.rate_limiter = {}
        self.rate_limit_max = int(os.getenv("GOOGLE_MAPS_RATE_LIMIT", "30"))
        
    def _get_secure_api_key(self) -> Optional[str]:
        """Retrieve and decrypt Google Maps API key"""
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            return None
            
        # If encryption key is available, decrypt the API key
        encryption_key = os.getenv("ENCRYPTION_KEY")
        if encryption_key and api_key.startswith("gAAAAAB"):  # Fernet encrypted format
            try:
                cipher = Fernet(encryption_key.encode())
                return cipher.decrypt(api_key.encode()).decode()
            except Exception as e:
                logger.warning(f"Failed to decrypt API key, using as-is: {e}")
        
        return api_key
    
    def get_function_specs(self) -> Dict[str, Any]:
        """Return function specifications for LLM integration"""
        return {
            "name": "google_maps_search",
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["search_places", "get_directions", "geocode", "nearby_search"],
                        "description": "The action to perform with Google Maps"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query for places (e.g., 'coffee shops', 'restaurants')"
                    },
                    "location": {
                        "type": "object",
                        "properties": {
                            "lat": {"type": "number", "minimum": -90, "maximum": 90},
                            "lng": {"type": "number", "minimum": -180, "maximum": 180}
                        },
                        "description": "Center location for search (latitude, longitude)"
                    },
                    "address": {
                        "type": "string",
                        "description": "Address to geocode or use as location reference"
                    },
                    "radius": {
                        "type": "integer",
                        "minimum": 100,
                        "maximum": 50000,
                        "default": 5000,
                        "description": "Search radius in meters (100-50000)"
                    },
                    "place_type": {
                        "type": "string",
                        "description": "Type of place to search for (restaurant, gas_station, etc.)"
                    },
                    "origin": {
                        "type": "string",
                        "description": "Starting point for directions"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination for directions"
                    },
                    "travel_mode": {
                        "type": "string",
                        "enum": ["driving", "walking", "transit", "bicycling"],
                        "default": "driving",
                        "description": "Mode of transportation for directions"
                    }
                },
                "required": ["action"]
            }
        }
    
    async def execute(self, params: Dict[str, Any], user_id: str = "anonymous") -> Dict[str, Any]:
        """Execute the function based on parameters"""
        try:
            # Validate input parameters
            if not self._validate_params(params):
                return {"error": "Invalid parameters provided", "type": "validation_error"}
            
            # Check rate limiting
            if not self._check_rate_limit(user_id):
                return {
                    "error": "Rate limit exceeded. Please wait a moment before trying again.",
                    "type": "rate_limit_error",
                    "retry_after": 60
                }
            
            action = params.get("action")
            
            # Route to appropriate handler
            if action == "search_places":
                return await self._search_places(params)
            elif action == "nearby_search":
                return await self._nearby_search(params)
            elif action == "get_directions":
                return await self._get_directions(params)
            elif action == "geocode":
                return await self._geocode_address(params)
            else:
                return {"error": f"Unknown action: {action}", "type": "invalid_action"}
                
        except googlemaps.exceptions.ApiError as e:
            logger.error(f"Google Maps API error: {e}")
            return {
                "error": "Google Maps service temporarily unavailable",
                "type": "api_error",
                "details": str(e) if os.getenv("DEBUG") else None
            }
        except Exception as e:
            logger.error(f"Unexpected error in Google Maps function: {e}")
            return {
                "error": "An unexpected error occurred",
                "type": "internal_error",
                "details": str(e) if os.getenv("DEBUG") else None
            }
    
    def _validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate input parameters"""
        action = params.get("action")
        if not action:
            return False
        
        # Validate based on action
        if action in ["search_places", "nearby_search"]:
            return bool(params.get("query") or params.get("place_type"))
        elif action == "get_directions":
            return bool(params.get("origin") and params.get("destination"))
        elif action == "geocode":
            return bool(params.get("address"))
        
        return False
    
    async def _search_places(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for places using text search"""
        # Generate cache key
        cache_key = self._generate_cache_key("text_search", params)
        
        # Check cache first
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            logger.info("Returning cached search results")
            return cached_result
        
        # Prepare search parameters
        query = params.get("query", "")
        location = params.get("location")
        
        search_params = {"query": query}
        if location:
            search_params["location"] = (location["lat"], location["lng"])
            search_params["radius"] = params.get("radius", 5000)
        
        # Execute search
        places_result = self.gmaps.places(**search_params)
        
        # Transform and limit results
        places = self._transform_places_result(places_result.get("results", [])[:10])
        
        result = {
            "type": "places_result",
            "action": "search_places",
            "places": places,
            "map_center": location or (places[0]["location"] if places else None),
            "search_query": query,
            "total_results": len(places),
            "timestamp": datetime.now().isoformat()
        }
        
        # Cache result
        await self._cache_result(cache_key, result)
        
        return result
    
    async def _nearby_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for nearby places"""
        location = params.get("location")
        if not location:
            return {"error": "Location is required for nearby search", "type": "validation_error"}
        
        cache_key = self._generate_cache_key("nearby_search", params)
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Prepare search parameters
        search_params = {
            "location": (location["lat"], location["lng"]),
            "radius": params.get("radius", 5000)
        }
        
        if params.get("place_type"):
            search_params["type"] = params["place_type"]
        if params.get("query"):
            search_params["keyword"] = params["query"]
        
        # Execute nearby search
        places_result = self.gmaps.places_nearby(**search_params)
        places = self._transform_places_result(places_result.get("results", [])[:10])
        
        result = {
            "type": "places_result",
            "action": "nearby_search",
            "places": places,
            "map_center": location,
            "search_params": {
                "radius": search_params["radius"],
                "type": params.get("place_type"),
                "keyword": params.get("query")
            },
            "total_results": len(places),
            "timestamp": datetime.now().isoformat()
        }
        
        await self._cache_result(cache_key, result)
        return result
    
    async def _get_directions(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get directions between two points"""
        origin = params.get("origin")
        destination = params.get("destination")
        travel_mode = params.get("travel_mode", "driving")
        
        cache_key = self._generate_cache_key("directions", params)
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Get directions
        directions_result = self.gmaps.directions(
            origin=origin,
            destination=destination,
            mode=travel_mode,
            alternatives=True,
            units="metric"
        )
        
        if not directions_result:
            return {
                "error": "No routes found between the specified locations",
                "type": "no_routes_found"
            }
        
        # Transform results
        routes = []
        for route in directions_result[:3]:  # Limit to 3 routes
            leg = route["legs"][0]
            routes.append({
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
                    for step in leg["steps"][:8]  # First 8 steps
                ],
                "polyline": route["overview_polyline"]["points"]
            })
        
        result = {
            "type": "directions_result",
            "action": "get_directions",
            "origin": origin,
            "destination": destination,
            "travel_mode": travel_mode,
            "routes": routes,
            "timestamp": datetime.now().isoformat()
        }
        
        await self._cache_result(cache_key, result)
        return result
    
    async def _geocode_address(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Geocode an address to get coordinates"""
        address = params.get("address")
        
        cache_key = self._generate_cache_key("geocode", params)
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        # Geocode the address
        geocode_result = self.gmaps.geocode(address)
        
        if not geocode_result:
            return {
                "error": f"Could not find location for address: {address}",
                "type": "geocoding_failed"
            }
        
        location_data = geocode_result[0]
        location = location_data["geometry"]["location"]
        
        result = {
            "type": "geocode_result",
            "action": "geocode",
            "address": address,
            "formatted_address": location_data["formatted_address"],
            "location": {
                "lat": location["lat"],
                "lng": location["lng"]
            },
            "place_id": location_data["place_id"],
            "types": location_data.get("types", []),
            "timestamp": datetime.now().isoformat()
        }
        
        await self._cache_result(cache_key, result)
        return result
    
    def _transform_places_result(self, places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform Google Maps places result to our format"""
        transformed = []
        for place in places:
            transformed_place = {
                "name": place.get("name", "Unknown"),
                "address": place.get("formatted_address", place.get("vicinity", "")),
                "location": {
                    "lat": place["geometry"]["location"]["lat"],
                    "lng": place["geometry"]["location"]["lng"]
                },
                "place_id": place.get("place_id"),
                "types": place.get("types", []),
                "rating": place.get("rating"),
                "user_ratings_total": place.get("user_ratings_total"),
                "price_level": place.get("price_level"),
                "business_status": place.get("business_status"),
                "permanently_closed": place.get("permanently_closed", False)
            }
            
            # Add photo reference if available
            photos = place.get("photos", [])
            if photos:
                transformed_place["photo_reference"] = photos[0].get("photo_reference")
            
            # Add opening hours if available
            if "opening_hours" in place:
                transformed_place["is_open"] = place["opening_hours"].get("open_now")
            
            transformed.append(transformed_place)
        
        return transformed
    
    def _clean_html(self, html_text: str) -> str:
        """Remove HTML tags from text"""
        import re
        clean = re.compile('<.*?>')
        return re.sub(clean, '', html_text)
    
    def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded rate limit"""
        now = datetime.now()
        user_requests = self.rate_limiter.get(user_id, [])
        
        # Remove requests older than 1 minute
        user_requests = [
            req for req in user_requests 
            if now - req < timedelta(minutes=1)
        ]
        
        if len(user_requests) >= self.rate_limit_max:
            return False
        
        user_requests.append(now)
        self.rate_limiter[user_id] = user_requests
        return True
    
    def _generate_cache_key(self, prefix: str, params: Dict[str, Any]) -> str:
        """Generate cache key from parameters"""
        # Create a deterministic string from params
        cache_params = {k: v for k, v in params.items() if k != "user_id"}
        param_str = json.dumps(cache_params, sort_keys=True)
        hash_obj = hashlib.md5(param_str.encode())
        return f"maps:{prefix}:{hash_obj.hexdigest()}"
    
    async def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if available"""
        if not self.redis_client:
            return None
        
        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
        
        return None
    
    async def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache the result"""
        if not self.redis_client:
            return
        
        try:
            ttl = int(os.getenv("GOOGLE_MAPS_CACHE_TTL", "300"))  # 5 minutes default
            self.redis_client.setex(
                cache_key, 
                ttl, 
                json.dumps(result, default=str)
            )
        except Exception as e:
            logger.warning(f"Cache storage failed: {e}")

# Function registration for Open WebUI
def get_function():
    """Return the function instance for Open WebUI"""
    return GoogleMapsFunction()

# For testing
if __name__ == "__main__":
    import asyncio
    
    async def test_function():
        function = GoogleMapsFunction()
        
        # Test place search
        result = await function.execute({
            "action": "search_places",
            "query": "coffee shops",
            "location": {"lat": 40.7128, "lng": -74.0060},
            "radius": 1000
        })
        
        print("Search result:", json.dumps(result, indent=2))
    
    asyncio.run(test_function())
