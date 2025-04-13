import logging
import requests
from sqlalchemy.exc import SQLAlchemyError
from models import db, CustomDomain

logger = logging.getLogger(__name__)

class DomainManager:
    """Manager for handling custom domains"""
    
    POPULAR_DOMAINS = [
        {"domain": "gmail.com", "display_name": "Gmail", "is_popular": True},
        {"domain": "hotmail.com", "display_name": "Hotmail", "is_popular": True},
        {"domain": "outlook.com", "display_name": "Outlook", "is_popular": True},
        {"domain": "yahoo.com", "display_name": "Yahoo", "is_popular": True},
        {"domain": "aol.com", "display_name": "AOL", "is_popular": True},
        {"domain": "protonmail.com", "display_name": "ProtonMail", "is_popular": True},
        {"domain": "icloud.com", "display_name": "iCloud", "is_popular": True},
        {"domain": "mail.com", "display_name": "Mail.com", "is_popular": True}
    ]
    
    def __init__(self):
        """Initialize the domain manager"""
        pass
    
    def init_app(self, app):
        """Initialize with the Flask app"""
        with app.app_context():
            self._initialize_popular_domains()
    
    def _initialize_popular_domains(self):
        """Initialize popular domain entries"""
        try:
            # Check if domains already exist
            existing_domains = CustomDomain.query.filter_by(is_popular=True).count()
            
            if existing_domains == 0:
                # Add popular domains
                for domain_data in self.POPULAR_DOMAINS:
                    domain = CustomDomain(
                        domain=domain_data["domain"],
                        display_name=domain_data["display_name"],
                        is_popular=domain_data["is_popular"],
                        is_active=True
                    )
                    db.session.add(domain)
                
                db.session.commit()
                logger.info(f"Added {len(self.POPULAR_DOMAINS)} popular domains")
            else:
                logger.debug(f"Popular domains already exist, skipping initialization")
                
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error initializing popular domains: {str(e)}")
    
    def get_all_domains(self, include_mail_tm=True, include_popular=True, include_custom=True):
        """Get all available domains"""
        domains = []
        
        # Get Mail.tm domains if requested
        if include_mail_tm:
            try:
                mail_tm_domains = self._get_mail_tm_domains()
                for domain in mail_tm_domains:
                    domains.append({
                        "id": f"mail_tm_{domain['id']}",
                        "domain": domain["domain"],
                        "display_name": f"Mail.tm ({domain['domain']})",
                        "type": "mail_tm"
                    })
            except Exception as e:
                logger.error(f"Error getting Mail.tm domains: {str(e)}")
        
        # Get popular domains if requested
        if include_popular:
            try:
                popular_domains = CustomDomain.query.filter_by(is_popular=True, is_active=True).all()
                for domain in popular_domains:
                    domains.append({
                        "id": f"popular_{domain.id}",
                        "domain": domain.domain,
                        "display_name": domain.display_name,
                        "type": "popular"
                    })
            except SQLAlchemyError as e:
                logger.error(f"Error getting popular domains: {str(e)}")
        
        # Get custom domains if requested
        if include_custom:
            try:
                custom_domains = CustomDomain.query.filter_by(is_popular=False, is_active=True).all()
                for domain in custom_domains:
                    domains.append({
                        "id": f"custom_{domain.id}",
                        "domain": domain.domain,
                        "display_name": domain.display_name,
                        "type": "custom"
                    })
            except SQLAlchemyError as e:
                logger.error(f"Error getting custom domains: {str(e)}")
        
        return domains
    
    def _get_mail_tm_domains(self):
        """Get available domains from Mail.tm"""
        MAIL_TM_API_BASE = "https://api.mail.tm"
        
        response = requests.get(f"{MAIL_TM_API_BASE}/domains")
        
        if response.status_code != 200 or 'hydra:member' not in response.json():
            logger.error(f"Failed to get domains from Mail.tm")
            return []
        
        return response.json()['hydra:member']
    
    def get_domain_by_id(self, domain_id):
        """Get domain details by ID"""
        if domain_id.startswith("mail_tm_"):
            # Mail.tm domain
            mail_tm_id = domain_id.replace("mail_tm_", "")
            domains = self._get_mail_tm_domains()
            for domain in domains:
                if domain["id"] == mail_tm_id:
                    return {
                        "id": domain_id,
                        "domain": domain["domain"],
                        "type": "mail_tm"
                    }
            return None
        
        elif domain_id.startswith("popular_") or domain_id.startswith("custom_"):
            # Popular or custom domain
            db_id = int(domain_id.split("_")[1])
            domain = CustomDomain.query.get(db_id)
            
            if domain and domain.is_active:
                return {
                    "id": domain_id,
                    "domain": domain.domain,
                    "type": "popular" if domain.is_popular else "custom"
                }
            
        return None
    
    def add_custom_domain(self, domain, display_name):
        """Add a new custom domain"""
        try:
            # Check if domain already exists
            existing = CustomDomain.query.filter_by(domain=domain).first()
            if existing:
                return False, "Domain already exists"
            
            # Create new domain
            new_domain = CustomDomain(
                domain=domain,
                display_name=display_name,
                is_popular=False,
                is_active=True
            )
            
            db.session.add(new_domain)
            db.session.commit()
            
            return True, f"Custom domain {domain} added successfully"
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error adding custom domain: {str(e)}")
            return False, "Database error adding domain"
    
    def update_domain_status(self, domain_id, is_active):
        """Enable or disable a domain"""
        try:
            if not domain_id.startswith(("popular_", "custom_")):
                return False, "Cannot update Mail.tm domains"
            
            db_id = int(domain_id.split("_")[1])
            domain = CustomDomain.query.get(db_id)
            
            if not domain:
                return False, "Domain not found"
            
            domain.is_active = is_active
            db.session.commit()
            
            status = "enabled" if is_active else "disabled"
            return True, f"Domain {domain.domain} {status} successfully"
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error updating domain status: {str(e)}")
            return False, "Database error updating domain"
    
    def get_domain_for_email_generation(self, domain_id=None):
        """Get domain information for email generation"""
        # If no domain_id provided, get first Mail.tm domain
        if not domain_id:
            domains = self._get_mail_tm_domains()
            if not domains:
                return None, "No domains available"
            
            return {
                "domain": domains[0]["domain"],
                "type": "mail_tm"
            }, None
        
        # Get domain details based on ID
        domain = self.get_domain_by_id(domain_id)
        if not domain:
            return None, "Domain not found or inactive"
        
        return domain, None