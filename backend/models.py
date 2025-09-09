"""
Pydantic models for API requests and responses
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class Location(BaseModel):
    """Geographic location"""
    lat: float = Field(..., description="Latitude", ge=-90, le=90)
    lng: float = Field(..., description="Longitude", ge=-180, le=180)


class Place(BaseModel):
    """Google Maps place information"""
    name: str
    place_id: str
    address: Optional[str] = None
    location: Location
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    price_level: Optional[int] = None
    types: List[str] = []
    is_open: Optional[bool] = None
    photo_reference: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None


class Route(BaseModel):
    """Directions route information"""
    summary: str
    distance: str
    duration: str
    start_address: str
    end_address: str
    steps: List[Dict[str, Any]]
    polyline: str


class ChatRequest(BaseModel):
    """Chat request from frontend"""
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = None
    user_location: Optional[Location] = None
    model: Optional[str] = "llama3"
    stream: bool = False


class ChatResponse(BaseModel):
    """Chat response to frontend"""
    message: str
    maps_data: Optional[Dict[str, Any]] = None
    conversation_id: Optional[str] = None
    timestamp: str
    model_used: Optional[str] = None


class MapsRequest(BaseModel):
    """Direct maps search request"""
    query: str = Field(..., min_length=1, max_length=200)
    location: Optional[str] = None
    radius: Optional[int] = Field(default=5000, ge=100, le=50000)
    place_type: Optional[str] = None
    max_results: Optional[int] = Field(default=10, ge=1, le=50)


class MapsResponse(BaseModel):
    """Maps search response"""
    places: List[Place]
    total_results: int
    search_query: str
    location: Optional[str] = None
    timestamp: str
    map_center: Optional[Location] = None


class DirectionsRequest(BaseModel):
    """Directions request"""
    origin: str = Field(..., min_length=1)
    destination: str = Field(..., min_length=1)
    travel_mode: str = Field(default="driving", regex="^(driving|walking|transit|bicycling)$")


class DirectionsResponse(BaseModel):
    """Directions response"""
    routes: List[Route]
    origin: str
    destination: str
    travel_mode: str
    timestamp: str


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    type: str
    timestamp: str
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""
    api: str
    llm: str
    google_maps: str
    redis: str
    timestamp: str


class ModelInfo(BaseModel):
    """LLM model information"""
    name: str
    size: Optional[str] = None
    modified: Optional[str] = None
    digest: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    type: str  # "message", "typing", "complete", "error"
    content: Optional[str] = None
    message: Optional[str] = None
    maps_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None
    user_id: Optional[str] = None
    location: Optional[Location] = None


class SystemStats(BaseModel):
    """System statistics"""
    total_requests: int
    active_connections: int
    cache_hit_rate: float
    average_response_time: float
    maps_api_calls: int
    llm_requests: int
    timestamp: str

