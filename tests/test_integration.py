"""
Integration tests for the complete system
Tests the interaction between components
"""

import pytest
import requests
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


class TestSystemIntegration:
    """Integration tests for the complete system"""
    
    BASE_URL = "http://localhost:3000"
    
    @pytest.fixture(scope="class")
    def wait_for_services(self):
        """Wait for all services to be ready"""
        max_retries = 30
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Check Open WebUI
                response = requests.get(f"{self.BASE_URL}/health", timeout=5)
                if response.status_code == 200:
                    break
            except requests.exceptions.RequestException:
                pass
            
            retry_count += 1
            time.sleep(2)
        
        if retry_count >= max_retries:
            pytest.skip("Services not ready for integration tests")
    
    def test_open_webui_health(self, wait_for_services):
        """Test that Open WebUI is responding"""
        response = requests.get(f"{self.BASE_URL}/health")
        assert response.status_code == 200
    
    def test_redis_connection(self):
        """Test Redis connectivity"""
        import redis
        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            assert r.ping() == True
        except redis.ConnectionError:
            pytest.skip("Redis not available for testing")
    
    def test_google_maps_function_registration(self, wait_for_services):
        """Test that Google Maps function is properly registered"""
        # This would test the function registration endpoint
        # Implementation depends on Open WebUI's API structure
        pass
    
    @pytest.mark.skipif(not pytest.config.getoption("--run-e2e"), 
                       reason="E2E tests require --run-e2e flag")
    def test_end_to_end_flow(self, wait_for_services):
        """Test complete user flow with browser automation"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            # Navigate to application
            driver.get(self.BASE_URL)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check if login is required
            if "sign" in driver.current_url.lower() or "login" in driver.current_url.lower():
                # Handle authentication if needed
                pass
            
            # Look for chat input
            chat_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'], textarea"))
            )
            
            # Type a location query
            test_query = "Find coffee shops near Times Square"
            chat_input.send_keys(test_query)
            
            # Find and click send button
            send_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], button:contains('Send')")
            send_button.click()
            
            # Wait for response (this might take a while for LLM processing)
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".message, .response"))
            )
            
            # Check if map component appears
            map_elements = driver.find_elements(By.CSS_SELECTOR, ".map-container, [class*='map']")
            assert len(map_elements) > 0, "Map component should be present in response"
            
        finally:
            driver.quit()


class TestAPIEndpoints:
    """Test API endpoints and responses"""
    
    BASE_URL = "http://localhost:3000"
    
    def test_api_health_check(self):
        """Test API health check endpoint"""
        try:
            response = requests.get(f"{self.BASE_URL}/health", timeout=5)
            assert response.status_code in [200, 404]  # 404 if endpoint doesn't exist
        except requests.exceptions.RequestException:
            pytest.skip("API not available for testing")
    
    def test_function_execution_endpoint(self):
        """Test function execution through API"""
        # This would test the actual function execution endpoint
        # Implementation depends on Open WebUI's API structure
        
        payload = {
            "function_id": "google_maps",
            "parameters": {
                "action": "search_places",
                "query": "coffee shops",
                "location": {"lat": 40.7128, "lng": -74.0060}
            }
        }
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/api/functions/execute",
                json=payload,
                timeout=10
            )
            
            # Check if endpoint exists and responds
            if response.status_code != 404:
                assert response.status_code in [200, 401, 403]  # Success or auth required
                
                if response.status_code == 200:
                    data = response.json()
                    assert "type" in data or "error" in data
                    
        except requests.exceptions.RequestException:
            pytest.skip("Function execution endpoint not available")


class TestPerformance:
    """Performance and load testing"""
    
    def test_response_time_benchmark(self):
        """Test that responses are within acceptable time limits"""
        # This would be implemented with actual performance testing tools
        # For now, just a placeholder
        pass
    
    def test_concurrent_requests(self):
        """Test system behavior under concurrent load"""
        # This would test multiple simultaneous requests
        # Implementation would use threading or async requests
        pass
    
    def test_cache_performance(self):
        """Test that caching improves response times"""
        # Test first request (cache miss) vs second request (cache hit)
        pass


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_api_key_handling(self):
        """Test behavior with invalid Google Maps API key"""
        # This would test the system's response to API key issues
        pass
    
    def test_rate_limit_handling(self):
        """Test rate limiting behavior"""
        # This would test making requests beyond the rate limit
        pass
    
    def test_network_failure_handling(self):
        """Test behavior when external services are unavailable"""
        # This would test graceful degradation
        pass


def pytest_addoption(parser):
    """Add command line options for pytest"""
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="Run end-to-end tests with browser automation"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--run-e2e"])
