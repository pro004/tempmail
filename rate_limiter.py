import time
import logging
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        # Dictionary to store request counts per IP and endpoint
        # Structure: {ip: {endpoint: [(timestamp, count), ...]}}
        self.request_counts = defaultdict(lambda: defaultdict(list))
        
        # Rate limit settings (requests per timeframe in seconds)
        self.rate_limits = {
            'generate_email': (5, 60),    # 5 requests per minute
            'get_emails': (60, 60),       # 60 requests per minute
            'get_email_content': (60, 60),# 60 requests per minute
            'delete_email': (30, 60),     # 30 requests per minute
            'delete_account': (5, 60)     # 5 requests per minute
        }
        
        # Default rate limit (20 requests per minute)
        self.default_rate_limit = (20, 60)
    
    def check_rate_limit(self, ip, endpoint):
        """
        Check if request is within rate limits
        Returns True if request is allowed, False otherwise
        """
        now = datetime.now()
        
        # Get rate limit for this endpoint
        max_requests, timeframe = self.rate_limits.get(endpoint, self.default_rate_limit)
        timeframe_delta = timedelta(seconds=timeframe)
        
        # Clean up old request counts
        self._cleanup_old_requests(ip, endpoint, now, timeframe_delta)
        
        # Count recent requests
        recent_requests = sum(count for timestamp, count in 
                            self.request_counts[ip][endpoint] 
                            if now - timestamp < timeframe_delta)
        
        # Check if rate limit exceeded
        if recent_requests >= max_requests:
            logger.warning(f"Rate limit exceeded: {ip} - {endpoint} - {recent_requests}/{max_requests}")
            return False
        
        # Update request count
        self._add_request(ip, endpoint, now)
        return True
    
    def _add_request(self, ip, endpoint, timestamp):
        """Add a request to the counter"""
        # Add new timestamp or increment last timestamp if it's the same second
        if (self.request_counts[ip][endpoint] and 
            (timestamp - self.request_counts[ip][endpoint][-1][0]).total_seconds() < 1):
            # Increment last timestamp count
            last_timestamp, count = self.request_counts[ip][endpoint][-1]
            self.request_counts[ip][endpoint][-1] = (last_timestamp, count + 1)
        else:
            # Add new timestamp
            self.request_counts[ip][endpoint].append((timestamp, 1))
    
    def _cleanup_old_requests(self, ip, endpoint, now, timeframe_delta):
        """Clean up request counts older than the timeframe"""
        if ip in self.request_counts and endpoint in self.request_counts[ip]:
            self.request_counts[ip][endpoint] = [
                (timestamp, count) for timestamp, count in self.request_counts[ip][endpoint]
                if now - timestamp < timeframe_delta
            ]
