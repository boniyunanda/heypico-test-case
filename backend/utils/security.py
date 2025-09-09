"""
Security utilities for input validation and token management
"""

import re
import logging
import hashlib
import secrets
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SecurityManager:
    """Handles security validation and token management"""
    
    def __init__(self):
        self.secret_key = secrets.token_urlsafe(32)
        
        # Dangerous patterns to detect
        self.dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # XSS
            r'javascript:',  # JavaScript injection
            r'on\w+\s*=',  # Event handlers
            r'eval\s*\(',  # Code execution
            r'exec\s*\(',  # Code execution
            r'system\s*\(',  # System calls
            r'__import__',  # Python imports
            r'subprocess',  # Process execution
            r'os\.',  # OS operations
            r'file://',  # File access
            r'data:.*base64',  # Data URLs
        ]
        
        # Compile patterns for performance
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.dangerous_patterns]
    
    def validate_input(self, text: str) -> bool:
        """Validate user input for security threats"""
        if not text or not isinstance(text, str):
            return False
        
        # Check length
        if len(text) > 5000:
            logger.warning("Input too long")
            return False
        
        # Check for dangerous patterns
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                logger.warning(f"Dangerous pattern detected: {pattern.pattern}")
                return False
        
        # Check for excessive special characters
        special_char_ratio = sum(1 for c in text if not c.isalnum() and not c.isspace()) / len(text)
        if special_char_ratio > 0.3:
            logger.warning("Too many special characters")
            return False
        
        return True
    
    def sanitize_input(self, text: str) -> str:
        """Sanitize user input"""
        if not text:
            return ""
        
        # Remove potential HTML/script tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Limit length
        return text[:2000]
    
    def generate_token(self, user_id: str, expires_in_hours: int = 24) -> str:
        """Generate JWT-like token for user"""
        # Simplified token generation (use proper JWT in production)
        timestamp = datetime.now().timestamp()
        expiry = timestamp + (expires_in_hours * 3600)
        
        payload = f"{user_id}:{expiry}:{timestamp}"
        signature = hashlib.sha256(f"{payload}:{self.secret_key}".encode()).hexdigest()
        
        return f"{payload}:{signature}"
    
    def validate_token(self, token: str) -> Optional[str]:
        """Validate token and return user_id"""
        try:
            parts = token.split(":")
            if len(parts) != 4:
                return None
            
            user_id, expiry, timestamp, signature = parts
            
            # Check signature
            payload = f"{user_id}:{expiry}:{timestamp}"
            expected_signature = hashlib.sha256(f"{payload}:{self.secret_key}".encode()).hexdigest()
            
            if signature != expected_signature:
                return None
            
            # Check expiry
            if float(expiry) < datetime.now().timestamp():
                return None
            
            return user_id
            
        except Exception as e:
            logger.warning(f"Token validation error: {e}")
            return None
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def validate_coordinates(self, lat: float, lng: float) -> bool:
        """Validate latitude and longitude"""
        return -90 <= lat <= 90 and -180 <= lng <= 180
    
    def validate_radius(self, radius: int) -> bool:
        """Validate search radius"""
        return 100 <= radius <= 50000
    
    def clean_html(self, html_text: str) -> str:
        """Remove HTML tags and dangerous content"""
        if not html_text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_text)
        
        # Remove dangerous content
        for pattern in self.compiled_patterns:
            text = pattern.sub('', text)
        
        return text.strip()

