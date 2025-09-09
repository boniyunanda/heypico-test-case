"""
Unit tests for Google Maps Function
Tests the core functionality, error handling, and security features
"""

import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import sys
import os

# Add the custom_functions directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'custom_functions'))

from google_maps import GoogleMapsFunction


class TestGoogleMapsFunction:
    """Test suite for Google Maps Function"""
    
    @pytest.fixture
    def mock_env(self):
        """Mock environment variables"""
        with patch.dict(os.environ, {
            'GOOGLE_MAPS_API_KEY': 'test-api-key',
            'REDIS_URL': 'redis://localhost:6379',
            'GOOGLE_MAPS_RATE_LIMIT': '30',
            'GOOGLE_MAPS_CACHE_TTL': '300'
        }):
            yield
    
    @pytest.fixture
    def mock_googlemaps(self):
        """Mock Google Maps client"""
        with patch('google_maps.googlemaps') as mock_gm:
            mock_client = MagicMock()
            mock_gm.Client.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        with patch('google_maps.redis') as mock_redis:
            mock_client = MagicMock()
            mock_redis.from_url.return_value = mock_client
            mock_client.ping.return_value = True
            yield mock_client
    
    @pytest.fixture
    def function_instance(self, mock_env, mock_googlemaps, mock_redis):
        """Create a GoogleMapsFunction instance with mocked dependencies"""
        return GoogleMapsFunction()
    
    def test_initialization(self, function_instance):
        """Test that the function initializes correctly"""
        assert function_instance.id == "google_maps"
        assert function_instance.name == "Google Maps Search"
        assert function_instance.version == "1.0.0"
        assert function_instance.rate_limit_max == 30
    
    def test_get_function_specs(self, function_instance):
        """Test function specifications for LLM integration"""
        specs = function_instance.get_function_specs()
        
        assert specs["name"] == "google_maps_search"
        assert "parameters" in specs
        assert "properties" in specs["parameters"]
        
        # Check required actions are present
        actions = specs["parameters"]["properties"]["action"]["enum"]
        expected_actions = ["search_places", "get_directions", "geocode", "nearby_search"]
        assert all(action in actions for action in expected_actions)
    
    @pytest.mark.asyncio
    async def test_search_places_success(self, function_instance, mock_googlemaps):
        """Test successful place search"""
        # Mock Google Maps API response
        mock_googlemaps.places.return_value = {
            "results": [{
                "name": "Test Coffee Shop",
                "formatted_address": "123 Test St, Test City",
                "geometry": {
                    "location": {"lat": 40.7128, "lng": -74.0060}
                },
                "place_id": "test-place-id",
                "rating": 4.5,
                "types": ["cafe", "food"],
                "user_ratings_total": 100
            }]
        }
        
        params = {
            "action": "search_places",
            "query": "coffee shops",
            "location": {"lat": 40.7128, "lng": -74.0060},
            "radius": 1000
        }
        
        result = await function_instance.execute(params, "test-user")
        
        assert result["type"] == "places_result"
        assert result["action"] == "search_places"
        assert len(result["places"]) == 1
        assert result["places"][0]["name"] == "Test Coffee Shop"
        assert result["search_query"] == "coffee shops"
        
        # Verify Google Maps API was called correctly
        mock_googlemaps.places.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_directions_success(self, function_instance, mock_googlemaps):
        """Test successful directions request"""
        # Mock Google Maps API response
        mock_googlemaps.directions.return_value = [{
            "summary": "Test Route",
            "legs": [{
                "distance": {"text": "2.5 km"},
                "duration": {"text": "8 mins"},
                "start_address": "Start Location",
                "end_address": "End Location",
                "steps": [{
                    "html_instructions": "Head <b>north</b> on Test St",
                    "distance": {"text": "0.5 km"},
                    "duration": {"text": "2 mins"},
                    "maneuver": "turn-left"
                }]
            }],
            "overview_polyline": {"points": "test-polyline-data"}
        }]
        
        params = {
            "action": "get_directions",
            "origin": "Start Location",
            "destination": "End Location",
            "travel_mode": "driving"
        }
        
        result = await function_instance.execute(params, "test-user")
        
        assert result["type"] == "directions_result"
        assert result["action"] == "get_directions"
        assert len(result["routes"]) == 1
        assert result["routes"][0]["distance"] == "2.5 km"
        assert result["routes"][0]["duration"] == "8 mins"
        
        # Verify API was called correctly
        mock_googlemaps.directions.assert_called_once_with(
            origin="Start Location",
            destination="End Location",
            mode="driving",
            alternatives=True,
            units="metric"
        )
    
    @pytest.mark.asyncio
    async def test_geocode_success(self, function_instance, mock_googlemaps):
        """Test successful geocoding"""
        # Mock Google Maps API response
        mock_googlemaps.geocode.return_value = [{
            "formatted_address": "Times Square, New York, NY, USA",
            "geometry": {
                "location": {"lat": 40.7580, "lng": -73.9855}
            },
            "place_id": "test-place-id",
            "types": ["establishment", "point_of_interest"]
        }]
        
        params = {
            "action": "geocode",
            "address": "Times Square, New York"
        }
        
        result = await function_instance.execute(params, "test-user")
        
        assert result["type"] == "geocode_result"
        assert result["action"] == "geocode"
        assert result["formatted_address"] == "Times Square, New York, NY, USA"
        assert result["location"]["lat"] == 40.7580
        assert result["location"]["lng"] == -73.9855
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, function_instance):
        """Test rate limiting functionality"""
        user_id = "test-user"
        
        # Make requests up to the limit
        for i in range(30):
            assert function_instance._check_rate_limit(user_id) == True
        
        # The 31st request should be rate limited
        assert function_instance._check_rate_limit(user_id) == False
    
    @pytest.mark.asyncio
    async def test_invalid_action(self, function_instance):
        """Test handling of invalid action"""
        params = {
            "action": "invalid_action",
            "query": "test"
        }
        
        result = await function_instance.execute(params, "test-user")
        
        assert "error" in result
        assert result["type"] == "invalid_action"
    
    @pytest.mark.asyncio
    async def test_missing_required_params(self, function_instance):
        """Test validation of required parameters"""
        # Test search_places without query or place_type
        params = {"action": "search_places"}
        result = await function_instance.execute(params, "test-user")
        assert result["type"] == "validation_error"
        
        # Test get_directions without origin
        params = {"action": "get_directions", "destination": "test"}
        result = await function_instance.execute(params, "test-user")
        assert result["type"] == "validation_error"
        
        # Test geocode without address
        params = {"action": "geocode"}
        result = await function_instance.execute(params, "test-user")
        assert result["type"] == "validation_error"
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, function_instance, mock_googlemaps):
        """Test handling of Google Maps API errors"""
        # Mock API error
        mock_googlemaps.places.side_effect = Exception("API Error")
        
        params = {
            "action": "search_places",
            "query": "coffee shops",
            "location": {"lat": 40.7128, "lng": -74.0060}
        }
        
        result = await function_instance.execute(params, "test-user")
        
        assert "error" in result
        assert result["type"] == "internal_error"
    
    @pytest.mark.asyncio
    async def test_caching_functionality(self, function_instance, mock_redis):
        """Test Redis caching functionality"""
        cache_key = "test-cache-key"
        test_data = {"test": "data"}
        
        # Test cache miss
        mock_redis.get.return_value = None
        result = await function_instance._get_cached_result(cache_key)
        assert result is None
        
        # Test cache hit
        mock_redis.get.return_value = json.dumps(test_data)
        result = await function_instance._get_cached_result(cache_key)
        assert result == test_data
        
        # Test cache storage
        await function_instance._cache_result(cache_key, test_data)
        mock_redis.setex.assert_called_once()
    
    def test_cache_key_generation(self, function_instance):
        """Test cache key generation is deterministic"""
        params1 = {"action": "search_places", "query": "coffee"}
        params2 = {"action": "search_places", "query": "coffee"}
        params3 = {"action": "search_places", "query": "tea"}
        
        key1 = function_instance._generate_cache_key("test", params1)
        key2 = function_instance._generate_cache_key("test", params2)
        key3 = function_instance._generate_cache_key("test", params3)
        
        # Same parameters should generate same key
        assert key1 == key2
        
        # Different parameters should generate different keys
        assert key1 != key3
    
    def test_places_result_transformation(self, function_instance):
        """Test transformation of Google Maps places results"""
        raw_places = [{
            "name": "Test Place",
            "formatted_address": "123 Test St",
            "geometry": {"location": {"lat": 40.7128, "lng": -74.0060}},
            "place_id": "test-id",
            "rating": 4.5,
            "types": ["restaurant"],
            "user_ratings_total": 100,
            "price_level": 2,
            "photos": [{"photo_reference": "test-photo"}],
            "opening_hours": {"open_now": True}
        }]
        
        transformed = function_instance._transform_places_result(raw_places)
        
        assert len(transformed) == 1
        place = transformed[0]
        
        assert place["name"] == "Test Place"
        assert place["address"] == "123 Test St"
        assert place["location"]["lat"] == 40.7128
        assert place["location"]["lng"] == -74.0060
        assert place["rating"] == 4.5
        assert place["price_level"] == 2
        assert place["photo_reference"] == "test-photo"
        assert place["is_open"] == True
    
    def test_html_cleaning(self, function_instance):
        """Test HTML tag removal from directions"""
        html_text = "Head <b>north</b> on <div>Test St</div>"
        cleaned = function_instance._clean_html(html_text)
        assert cleaned == "Head north on Test St"
    
    @pytest.mark.asyncio
    async def test_nearby_search(self, function_instance, mock_googlemaps):
        """Test nearby search functionality"""
        mock_googlemaps.places_nearby.return_value = {
            "results": [{
                "name": "Nearby Place",
                "geometry": {"location": {"lat": 40.7128, "lng": -74.0060}},
                "place_id": "nearby-place-id",
                "types": ["restaurant"]
            }]
        }
        
        params = {
            "action": "nearby_search",
            "location": {"lat": 40.7128, "lng": -74.0060},
            "place_type": "restaurant",
            "radius": 500
        }
        
        result = await function_instance.execute(params, "test-user")
        
        assert result["type"] == "places_result"
        assert result["action"] == "nearby_search"
        assert len(result["places"]) == 1
        
        # Verify API was called with correct parameters
        mock_googlemaps.places_nearby.assert_called_once()
        call_args = mock_googlemaps.places_nearby.call_args[1]
        assert call_args["location"] == (40.7128, -74.0060)
        assert call_args["radius"] == 500
        assert call_args["type"] == "restaurant"


class TestSecurityFeatures:
    """Test security-related functionality"""
    
    @pytest.fixture
    def function_instance(self):
        with patch.dict(os.environ, {'GOOGLE_MAPS_API_KEY': 'test-key'}):
            with patch('google_maps.googlemaps'):
                with patch('google_maps.redis') as mock_redis:
                    mock_redis.from_url.return_value.ping.return_value = True
                    return GoogleMapsFunction()
    
    def test_parameter_validation(self, function_instance):
        """Test input parameter validation"""
        # Valid parameters
        assert function_instance._validate_params({
            "action": "search_places",
            "query": "coffee"
        }) == True
        
        assert function_instance._validate_params({
            "action": "get_directions",
            "origin": "A",
            "destination": "B"
        }) == True
        
        # Invalid parameters
        assert function_instance._validate_params({
            "action": "search_places"
        }) == False
        
        assert function_instance._validate_params({
            "action": "get_directions",
            "origin": "A"
        }) == False
        
        assert function_instance._validate_params({}) == False
    
    def test_rate_limit_cleanup(self, function_instance):
        """Test that old rate limit entries are cleaned up"""
        user_id = "test-user"
        
        # Add old entries
        old_time = datetime.now() - timedelta(minutes=2)
        function_instance.rate_limiter[user_id] = [old_time] * 30
        
        # New request should succeed (old entries cleaned up)
        assert function_instance._check_rate_limit(user_id) == True
        
        # Should only have 1 entry now (the new one)
        assert len(function_instance.rate_limiter[user_id]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
