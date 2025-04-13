import random
import string
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TempMailStorage:
    """In-memory storage for temporary email accounts"""
    
    def __init__(self):
        # Dictionary to store account data
        # Key: email address
        # Value: dict with id, token, password, created_at
        self.accounts = {}
        
    def generate_random_string(self, length=10):
        """Generate a random string of fixed length"""
        chars = string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    def add_account(self, email, account_data):
        """Add a new account to storage"""
        # Add timestamp for expiration
        account_data['created_at'] = datetime.now()
        self.accounts[email] = account_data
        logger.debug(f"Added account: {email}")
        
        # Clean up old accounts
        self._cleanup_old_accounts()
        
        return True
    
    def get_account(self, email):
        """Get account data for a specific email"""
        account_data = self.accounts.get(email)
        
        if not account_data:
            logger.debug(f"Account not found: {email}")
            return None
            
        # Check if account is expired (24 hours)
        created_at = account_data.get('created_at')
        if created_at and datetime.now() - created_at > timedelta(hours=24):
            logger.debug(f"Account expired: {email}")
            self.remove_account(email)
            return None
            
        return account_data
    
    def remove_account(self, email):
        """Remove an account from storage"""
        if email in self.accounts:
            del self.accounts[email]
            logger.debug(f"Removed account: {email}")
            return True
        return False
    
    def _cleanup_old_accounts(self):
        """Remove accounts older than 24 hours"""
        now = datetime.now()
        to_remove = []
        
        for email, account_data in self.accounts.items():
            created_at = account_data.get('created_at')
            if created_at and now - created_at > timedelta(hours=24):
                to_remove.append(email)
                
        for email in to_remove:
            self.remove_account(email)
            
        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} old accounts")
