"""
Ollama LLM Service
Handles local LLM interactions with function calling for Google Maps
"""

import asyncio
import json
import logging
import re
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
import httpx

from services.cache_service import CacheService
from services.maps_service import GoogleMapsService

logger = logging.getLogger(__name__)


class OllamaService:
    """Local LLM service using Ollama"""
    
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
        self.base_url = "http://localhost:11434"
        self.model = "llama3"
        self.maps_service = None  # Will be injected
        
        # System prompt for location awareness
        self.system_prompt = """
You are a helpful assistant with access to Google Maps. When users ask about:
- Finding places (restaurants, coffee shops, gas stations, etc.)
- Getting directions between locations
- Location information or addresses

You should use the available Google Maps functions to provide accurate, real-time information.

Always format your responses with:
1. A brief introduction
2. The search results with details
3. Helpful suggestions or additional information

When displaying places, include:
- Name and address
- Ratings if available
- Whether it's open/closed
- Direct Google Maps links

Be conversational and helpful!
"""
    
    def set_maps_service(self, maps_service: GoogleMapsService):
        """Inject maps service for function calling"""
        self.maps_service = maps_service
    
    async def health_check(self) -> bool:
        """Check if Ollama is running and model is available"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json()
                    model_names = [model["name"] for model in models.get("models", [])]
                    return self.model in model_names or f"{self.model}:latest" in model_names
                return False
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    async def get_models(self) -> List[str]:
        """Get available models from Ollama"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json()
                    return [model["name"] for model in models.get("models", [])]
                return []
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return []
    
    async def load_model(self, model_name: str) -> bool:
        """Load a specific model"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/pull",
                    json={"name": model_name}
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            return False
    
    async def process_message(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        user_location: Optional[Dict[str, float]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Process user message with LLM and handle location queries
        """
        try:
            # Detect if this is a location-related query
            is_location_query = self._detect_location_intent(message)
            
            # If location query, try to extract location info and search
            maps_data = None
            if is_location_query and self.maps_service:
                maps_data = await self._handle_location_query(message, user_location)
            
            # Generate LLM response
            llm_response = await self._generate_llm_response(
                message, maps_data, conversation_id, stream
            )
            
            return {
                "text": llm_response,
                "maps_data": maps_data,
                "timestamp": datetime.now().isoformat(),
                "model": self.model,
                "conversation_id": conversation_id
            }
            
        except Exception as e:
            logger.error(f"Message processing error: {e}")
            return {
                "text": "I apologize, but I encountered an error processing your request. Please try again.",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _detect_location_intent(self, message: str) -> bool:
        """Detect if message is asking about locations"""
        location_keywords = [
            "find", "search", "near", "nearby", "close to", "around",
            "restaurant", "cafe", "coffee", "food", "eat", "drink",
            "gas station", "hotel", "hospital", "bank", "store",
            "directions", "route", "how to get", "navigate",
            "address", "location", "coordinates", "map"
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in location_keywords)
    
    async def _handle_location_query(
        self,
        message: str,
        user_location: Optional[Dict[str, float]] = None
    ) -> Optional[Dict[str, Any]]:
        """Extract location information and search Google Maps"""
        try:
            # Extract search parameters from message
            search_params = self._extract_search_params(message, user_location)
            
            if search_params["type"] == "search_places":
                return await self.maps_service.search_places(
                    query=search_params["query"],
                    location=search_params.get("location"),
                    radius=search_params.get("radius", 5000)
                )
            
            elif search_params["type"] == "directions":
                return await self.maps_service.get_directions(
                    origin=search_params["origin"],
                    destination=search_params["destination"],
                    travel_mode=search_params.get("travel_mode", "driving")
                )
            
            elif search_params["type"] == "geocode":
                return await self.maps_service.geocode_address(search_params["address"])
            
            return None
            
        except Exception as e:
            logger.error(f"Location query handling error: {e}")
            return None
    
    def _extract_search_params(self, message: str, user_location: Optional[Dict[str, float]]) -> Dict[str, Any]:
        """Extract search parameters from natural language"""
        message_lower = message.lower()
        
        # Check for directions
        direction_patterns = [
            r"directions? (?:from |to )?(.+?) to (.+?)(?:\s|$)",
            r"how (?:do i|to) get (?:from )?(.+?) to (.+?)(?:\s|$)",
            r"route (?:from )?(.+?) to (.+?)(?:\s|$)",
            r"navigate (?:from )?(.+?) to (.+?)(?:\s|$)"
        ]
        
        for pattern in direction_patterns:
            match = re.search(pattern, message_lower)
            if match:
                return {
                    "type": "directions",
                    "origin": match.group(1).strip(),
                    "destination": match.group(2).strip(),
                    "travel_mode": self._extract_travel_mode(message)
                }
        
        # Check for address lookup
        if "address" in message_lower or "coordinates" in message_lower:
            address_match = re.search(r"(?:address|coordinates) (?:of |for )?(.+?)(?:\s|$)", message_lower)
            if address_match:
                return {
                    "type": "geocode",
                    "address": address_match.group(1).strip()
                }
        
        # Default to place search
        query = self._extract_place_query(message)
        location = self._extract_location(message, user_location)
        
        return {
            "type": "search_places",
            "query": query,
            "location": location,
            "radius": self._extract_radius(message)
        }
    
    def _extract_place_query(self, message: str) -> str:
        """Extract what the user is looking for"""
        # Remove common location words to get the core query
        location_words = ["near", "around", "close to", "in", "at", "by"]
        words = message.split()
        
        # Find where location context starts
        query_words = []
        for word in words:
            if word.lower() in location_words:
                break
            query_words.append(word)
        
        # Remove action words
        action_words = ["find", "search", "look for", "show me", "get", "where"]
        filtered_words = [w for w in query_words if w.lower() not in action_words]
        
        return " ".join(filtered_words) if filtered_words else "places"
    
    def _extract_location(self, message: str, user_location: Optional[Dict[str, float]]) -> Optional[str]:
        """Extract location from message"""
        message_lower = message.lower()
        
        # Look for "near X" patterns
        near_patterns = [
            r"near (.+?)(?:\s|$)",
            r"around (.+?)(?:\s|$)",
            r"close to (.+?)(?:\s|$)",
            r"in (.+?)(?:\s|$)",
            r"at (.+?)(?:\s|$)"
        ]
        
        for pattern in near_patterns:
            match = re.search(pattern, message_lower)
            if match:
                location = match.group(1).strip()
                # Remove trailing punctuation
                location = re.sub(r'[.!?]+$', '', location)
                return location
        
        # Check for coordinates
        coord_pattern = r"(-?\d+\.?\d*),\s*(-?\d+\.?\d*)"
        coord_match = re.search(coord_pattern, message)
        if coord_match:
            return f"{coord_match.group(1)},{coord_match.group(2)}"
        
        # Use user location if provided
        if user_location:
            return f"{user_location['lat']},{user_location['lng']}"
        
        return None
    
    def _extract_radius(self, message: str) -> int:
        """Extract search radius from message"""
        # Look for distance mentions
        radius_patterns = [
            (r"within (\d+)\s*(?:km|kilometer)", lambda x: int(x) * 1000),
            (r"within (\d+)\s*(?:m|meter)", lambda x: int(x)),
            (r"within (\d+)\s*(?:mile)", lambda x: int(x) * 1609),
            (r"(\d+)\s*(?:km|kilometer) radius", lambda x: int(x) * 1000),
            (r"(\d+)\s*(?:mile) radius", lambda x: int(x) * 1609)
        ]
        
        message_lower = message.lower()
        for pattern, converter in radius_patterns:
            match = re.search(pattern, message_lower)
            if match:
                try:
                    return min(converter(match.group(1)), 50000)  # Max 50km
                except ValueError:
                    continue
        
        return 5000  # Default 5km
    
    def _extract_travel_mode(self, message: str) -> str:
        """Extract travel mode from message"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["walk", "walking", "on foot"]):
            return "walking"
        elif any(word in message_lower for word in ["bike", "bicycle", "cycling"]):
            return "bicycling"
        elif any(word in message_lower for word in ["transit", "public transport", "subway", "bus"]):
            return "transit"
        else:
            return "driving"
    
    async def _generate_llm_response(
        self,
        message: str,
        maps_data: Optional[Dict[str, Any]],
        conversation_id: Optional[str],
        stream: bool = False
    ) -> str:
        """Generate response using Ollama LLM"""
        try:
            # Prepare prompt with maps data if available
            prompt = self._build_prompt(message, maps_data)
            
            # Call Ollama API
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "top_p": 0.9,
                            "max_tokens": 1000
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "I apologize, but I couldn't generate a response.")
                else:
                    logger.error(f"Ollama API error: {response.status_code}")
                    return "I'm having trouble connecting to the language model. Please try again."
        
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            return "I encountered an error while processing your request. Please try again."
    
    def _build_prompt(self, message: str, maps_data: Optional[Dict[str, Any]]) -> str:
        """Build prompt with system context and maps data"""
        prompt = f"{self.system_prompt}\n\nUser: {message}\n\n"
        
        if maps_data:
            if "places" in maps_data:
                places = maps_data["places"]
                prompt += f"I found {len(places)} places for your query:\n\n"
                
                for i, place in enumerate(places[:8], 1):
                    prompt += f"{i}. **{place['name']}**\n"
                    if place.get('address'):
                        prompt += f"   Address: {place['address']}\n"
                    if place.get('rating'):
                        prompt += f"   Rating: ⭐ {place['rating']}"
                        if place.get('user_ratings_total'):
                            prompt += f" ({place['user_ratings_total']} reviews)"
                        prompt += "\n"
                    if place.get('price_level'):
                        prompt += f"   Price: {'$' * place['price_level']}\n"
                    if place.get('is_open') is not None:
                        status = "🟢 Open" if place['is_open'] else "🔴 Closed"
                        prompt += f"   Status: {status}\n"
                    
                    # Add Google Maps link
                    if place.get('place_id'):
                        maps_url = f"https://maps.google.com/maps/place/?q=place_id:{place['place_id']}"
                        prompt += f"   Google Maps: {maps_url}\n"
                    
                    prompt += "\n"
            
            elif "routes" in maps_data:
                routes = maps_data["routes"]
                route = routes[0] if routes else None
                if route:
                    prompt += f"I found directions from {maps_data['origin']} to {maps_data['destination']}:\n\n"
                    prompt += f"Distance: {route['distance']} | Duration: {route['duration']}\n\n"
                    prompt += "Key directions:\n"
                    
                    for i, step in enumerate(route['steps'][:8], 1):
                        prompt += f"{i}. {step['instruction']} ({step['distance']})\n"
                    
                    if len(route['steps']) > 8:
                        prompt += f"... and {len(route['steps']) - 8} more steps\n"
        
        prompt += "\nAssistant: "
        return prompt
    
    async def generate_streaming_response(
        self,
        message: str,
        maps_data: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response from LLM"""
        try:
            prompt = self._build_prompt(message, maps_data)
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": True,
                        "options": {
                            "temperature": 0.7,
                            "top_p": 0.9
                        }
                    }
                ) as response:
                    
                    if response.status_code != 200:
                        yield "Error: Failed to connect to language model"
                        return
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                chunk = json.loads(line)
                                if "response" in chunk:
                                    yield chunk["response"]
                                if chunk.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
        
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"Error: {str(e)}"

