"""
FastAPI Backend for Local LLM with Google Maps Integration
Production-ready API with comprehensive error handling and security
"""

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
import redis.asyncio as redis
import httpx

from models import ChatRequest, ChatResponse, MapsRequest, MapsResponse
from services.maps_service import GoogleMapsService
from services.llm_service import OllamaService
from services.cache_service import CacheService
from utils.security import SecurityManager
from utils.rate_limiter import RateLimiter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global services
maps_service: GoogleMapsService
llm_service: OllamaService
cache_service: CacheService
security_manager: SecurityManager
rate_limiter: RateLimiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting Local LLM Maps API...")
    
    # Initialize services
    global maps_service, llm_service, cache_service, security_manager, rate_limiter
    
    try:
        # Initialize Redis
        redis_client = redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379"),
            decode_responses=True
        )
        await redis_client.ping()
        logger.info("✅ Redis connected")
        
        # Initialize services
        cache_service = CacheService(redis_client)
        security_manager = SecurityManager()
        rate_limiter = RateLimiter(redis_client)
        maps_service = GoogleMapsService(cache_service)
        llm_service = OllamaService(cache_service)
        
        # Test LLM connection
        await llm_service.health_check()
        logger.info("✅ Ollama LLM connected")
        
        # Test Google Maps
        await maps_service.health_check()
        logger.info("✅ Google Maps API connected")
        
        logger.info("🎉 All services initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🔄 Shutting down services...")
    if redis_client:
        await redis_client.close()


# Create FastAPI app
app = FastAPI(
    title="Local LLM with Google Maps",
    description="Production-ready API for Local LLM with Google Maps integration",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer(auto_error=False)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[str]:
    """Extract user from token (simplified for demo)"""
    if credentials:
        return security_manager.validate_token(credentials.credentials)
    return "anonymous"


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Local LLM with Google Maps API",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    health_status = {
        "api": "healthy",
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # Check LLM
        llm_status = await llm_service.health_check()
        health_status["llm"] = "healthy" if llm_status else "unhealthy"
    except Exception as e:
        health_status["llm"] = f"error: {str(e)}"
    
    try:
        # Check Google Maps
        maps_status = await maps_service.health_check()
        health_status["google_maps"] = "healthy" if maps_status else "unhealthy"
    except Exception as e:
        health_status["google_maps"] = f"error: {str(e)}"
    
    try:
        # Check Redis
        await cache_service.ping()
        health_status["redis"] = "healthy"
    except Exception as e:
        health_status["redis"] = f"error: {str(e)}"
    
    return health_status


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_llm(
    request: ChatRequest,
    user: str = Depends(get_current_user)
):
    """
    Chat with LLM and get location-based responses
    """
    try:
        # Rate limiting
        if not await rate_limiter.check_limit(user):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Security validation
        if not security_manager.validate_input(request.message):
            raise HTTPException(status_code=400, detail="Invalid input detected")
        
        # Process with LLM
        response = await llm_service.process_message(
            message=request.message,
            conversation_id=request.conversation_id,
            user_location=request.user_location
        )
        
        return ChatResponse(
            message=response["text"],
            maps_data=response.get("maps_data"),
            conversation_id=request.conversation_id,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/maps/search", response_model=MapsResponse)
async def search_places(
    request: MapsRequest,
    user: str = Depends(get_current_user)
):
    """
    Direct Google Maps search endpoint
    """
    try:
        # Rate limiting
        if not await rate_limiter.check_limit(user, endpoint="maps"):
            raise HTTPException(status_code=429, detail="Maps API rate limit exceeded")
        
        # Execute search
        result = await maps_service.search_places(
            query=request.query,
            location=request.location,
            radius=request.radius,
            place_type=request.place_type
        )
        
        return MapsResponse(**result)
        
    except Exception as e:
        logger.error(f"Maps search error: {e}")
        raise HTTPException(status_code=500, detail="Maps search failed")


@app.post("/api/maps/directions")
async def get_directions(
    origin: str,
    destination: str,
    travel_mode: str = "driving",
    user: str = Depends(get_current_user)
):
    """
    Get directions between two points
    """
    try:
        # Rate limiting
        if not await rate_limiter.check_limit(user, endpoint="directions"):
            raise HTTPException(status_code=429, detail="Directions API rate limit exceeded")
        
        result = await maps_service.get_directions(
            origin=origin,
            destination=destination,
            travel_mode=travel_mode
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Directions error: {e}")
        raise HTTPException(status_code=500, detail="Directions failed")


@app.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    """
    WebSocket endpoint for real-time chat
    """
    await websocket.accept()
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Security validation
            if not security_manager.validate_input(message_data.get("message", "")):
                await websocket.send_text(json.dumps({
                    "error": "Invalid input detected",
                    "type": "security_error"
                }))
                continue
            
            # Rate limiting
            user_id = message_data.get("user_id", "anonymous")
            if not await rate_limiter.check_limit(user_id, endpoint="websocket"):
                await websocket.send_text(json.dumps({
                    "error": "Rate limit exceeded",
                    "type": "rate_limit"
                }))
                continue
            
            # Send typing indicator
            await websocket.send_text(json.dumps({
                "type": "typing",
                "status": "processing"
            }))
            
            # Process with LLM
            try:
                response = await llm_service.process_message(
                    message=message_data["message"],
                    conversation_id=conversation_id,
                    user_location=message_data.get("location"),
                    stream=True
                )
                
                # Stream response
                if response.get("stream"):
                    async for chunk in response["stream"]:
                        await websocket.send_text(json.dumps({
                            "type": "stream",
                            "content": chunk
                        }))
                
                # Send final response with maps data
                await websocket.send_text(json.dumps({
                    "type": "complete",
                    "message": response["text"],
                    "maps_data": response.get("maps_data"),
                    "timestamp": datetime.now().isoformat()
                }))
                
            except Exception as e:
                logger.error(f"WebSocket processing error: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Failed to process message",
                    "error": str(e)
                }))
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for conversation {conversation_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close(code=1000)


@app.get("/api/models")
async def get_available_models():
    """Get available LLM models"""
    try:
        models = await llm_service.get_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Models error: {e}")
        return {"models": [], "error": str(e)}


@app.post("/api/models/{model_name}/load")
async def load_model(model_name: str):
    """Load a specific LLM model"""
    try:
        success = await llm_service.load_model(model_name)
        return {"success": success, "model": model_name}
    except Exception as e:
        logger.error(f"Model loading error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load model")


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

