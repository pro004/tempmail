import logging
import random
import string
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from models import db, TempEmail, Email

logger = logging.getLogger(__name__)

class DatabaseTempMailStorage:
    """Database storage for temporary email accounts"""
    
    def generate_random_string(self, length=10):
        """Generate a random string of fixed length"""
        chars = string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    def add_account(self, email, account_data):
        """Add a new account to database"""
        try:
            new_account = TempEmail(
                email=email,
                account_id=account_data['id'],
                token=account_data['token'],
                password=account_data['password'],
                created_at=datetime.now(),
                is_active=True
            )
            
            db.session.add(new_account)
            db.session.commit()
            logger.debug(f"Added account to database: {email}")
            
            # Clean up old accounts
            self._cleanup_old_accounts()
            
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error adding account: {str(e)}")
            return False
    
    def get_account(self, email):
        """Get account data for a specific email"""
        try:
            account = TempEmail.query.filter_by(email=email, is_active=True).first()
            
            if not account:
                logger.debug(f"Account not found in database: {email}")
                return None
                
            # Check if account is expired (24 hours)
            if account.is_expired:
                logger.debug(f"Account expired: {email}")
                self.remove_account(email)
                return None
                
            return {
                'id': account.account_id,
                'token': account.token,
                'password': account.password
            }
        except SQLAlchemyError as e:
            logger.error(f"Database error getting account: {str(e)}")
            return None
    
    def remove_account(self, email):
        """Remove an account from database"""
        try:
            account = TempEmail.query.filter_by(email=email).first()
            if not account:
                return False
                
            account.is_active = False
            db.session.commit()
            logger.debug(f"Marked account as inactive: {email}")
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error removing account: {str(e)}")
            return False
    
    def _cleanup_old_accounts(self):
        """Mark accounts older than 24 hours as inactive"""
        try:
            expiration_date = datetime.now() - timedelta(hours=24)
            old_accounts = TempEmail.query.filter(
                TempEmail.created_at < expiration_date,
                TempEmail.is_active == True
            ).all()
            
            for account in old_accounts:
                account.is_active = False
                
            db.session.commit()
            
            if old_accounts:
                logger.debug(f"Cleaned up {len(old_accounts)} old accounts")
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error during cleanup: {str(e)}")
    
    def save_email(self, email_address, email_data):
        """Save an email to the database"""
        try:
            # Get the temp email account
            account = TempEmail.query.filter_by(email=email_address, is_active=True).first()
            if not account:
                logger.error(f"Cannot save email: account not found for {email_address}")
                return False
            
            # Check if email already exists
            existing_email = Email.query.filter_by(
                message_id=email_data.get('id'),
                temp_email_id=account.id
            ).first()
            
            if existing_email:
                # Update read status if needed
                if existing_email.is_read != email_data.get('seen', False):
                    existing_email.is_read = email_data.get('seen', False)
                    db.session.commit()
                return True
            
            # Create new email record
            new_email = Email(
                message_id=email_data.get('id'),
                temp_email_id=account.id,
                sender=email_data.get('from', {}).get('address'),
                recipient=email_address,
                subject=email_data.get('subject'),
                intro=email_data.get('intro'),
                html_content=email_data.get('html'),
                text_content=email_data.get('text'),
                is_read=email_data.get('seen', False),
                created_at=datetime.fromisoformat(email_data.get('createdAt').replace('Z', '+00:00'))
            )
            
            db.session.add(new_email)
            db.session.commit()
            logger.debug(f"Saved email to database: {email_data.get('id')}")
            return True
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error saving email: {str(e)}")
            return False
    
    def mark_email_as_read(self, email_address, message_id):
        """Mark an email as read"""
        try:
            account = TempEmail.query.filter_by(email=email_address, is_active=True).first()
            if not account:
                return False
                
            email = Email.query.filter_by(
                message_id=message_id,
                temp_email_id=account.id
            ).first()
            
            if email:
                email.is_read = True
                db.session.commit()
                logger.debug(f"Marked email as read: {message_id}")
                return True
            return False
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error marking email as read: {str(e)}")
            return False
    
    def delete_email(self, email_address, message_id):
        """Delete an email from the database"""
        try:
            account = TempEmail.query.filter_by(email=email_address, is_active=True).first()
            if not account:
                return False
                
            email = Email.query.filter_by(
                message_id=message_id,
                temp_email_id=account.id
            ).first()
            
            if email:
                db.session.delete(email)
                db.session.commit()
                logger.debug(f"Deleted email: {message_id}")
                return True
            return False
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error deleting email: {str(e)}")
            return False
    
    def get_emails(self, email_address):
        """Get all emails for a specific email address"""
        try:
            account = TempEmail.query.filter_by(email=email_address, is_active=True).first()
            if not account:
                return []
                
            emails = Email.query.filter_by(temp_email_id=account.id).order_by(Email.created_at.desc()).all()
            return [email.to_dict() for email in emails]
        except SQLAlchemyError as e:
            logger.error(f"Database error getting emails: {str(e)}")
            return []
    
    def get_email(self, email_address, message_id):
        """Get a specific email"""
        try:
            account = TempEmail.query.filter_by(email=email_address, is_active=True).first()
            if not account:
                return None
                
            email = Email.query.filter_by(
                message_id=message_id,
                temp_email_id=account.id
            ).first()
            
            if email:
                return email.to_dict(include_content=True)
            return None
        except SQLAlchemyError as e:
            logger.error(f"Database error getting email: {str(e)}")
            return None