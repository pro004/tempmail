import logging
import requests
import json
import uuid
import random
import string
from datetime import datetime
from flask import request, jsonify, Blueprint
from db_storage import DatabaseTempMailStorage
from rate_limiter import RateLimiter

# Configure logging
logger = logging.getLogger(__name__)

# Base URL for Mail.tm API
MAIL_TM_API_BASE = "https://api.mail.tm"

# Initialize storage and rate limiter
storage = DatabaseTempMailStorage()
rate_limiter = RateLimiter()

# Create blueprints
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/domains', methods=['GET'])
def get_domains():
    """Get all available domains"""
    # Check rate limit
    client_ip = request.remote_addr
    if not rate_limiter.check_rate_limit(client_ip, 'get_domains'):
        return jsonify({"error": "Rate limit exceeded"}), 429
    
    try:
        # Get domains from domain manager
        from app import domain_manager
        domains = domain_manager.get_all_domains()
        
        return jsonify({
            "domains": domains
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting domains: {str(e)}")
        return jsonify({"error": "Failed to get domains"}), 500

@api_bp.route('/generate', methods=['POST'])
def generate_email():
    """Generate a new temporary email address"""
    # Check rate limit
    client_ip = request.remote_addr
    if not rate_limiter.check_rate_limit(client_ip, 'generate_email'):
        return jsonify({"error": "Rate limit exceeded"}), 429
    
    try:
        # Get domain ID from request (optional)
        data = request.get_json() or {}
        domain_id = data.get('domain_id')
        username_input = data.get('username', '').lower() if data else ''
        
        # If no username provided, generate a random one
        if not username_input:
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        else:
            username = username_input
        
        # Get domain info from domain manager
        from app import domain_manager
        domain_info, error = domain_manager.get_domain_for_email_generation(domain_id)
        
        if error:
            return jsonify({"error": error}), 400
        
        domain_type = domain_info.get('type')
        domain = domain_info.get('domain')
        
        # Generate password
        password = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        
        # If using Mail.tm domain, create account there
        if domain_type == 'mail_tm':
            email = f"{username}@{domain}"
            
            # Create account on Mail.tm
            account_data = {
                "address": email,
                "password": password
            }
            
            create_response = requests.post(
                f"{MAIL_TM_API_BASE}/accounts", 
                json=account_data
            )
            
            if create_response.status_code != 201:
                logger.error(f"Failed to create account: {create_response.text}")
                return jsonify({"error": "Failed to create temporary email"}), 500
            
            # Get token for authentication
            token_data = {
                "address": email,
                "password": password
            }
            
            token_response = requests.post(
                f"{MAIL_TM_API_BASE}/token", 
                json=token_data
            )
            
            if token_response.status_code != 200:
                logger.error(f"Failed to get token: {token_response.text}")
                return jsonify({"error": "Failed to authenticate with temporary email"}), 500
            
            token = token_response.json().get('token')
            account_id = create_response.json().get('id')
            
            # Store account information
            storage.add_account(email, {
                "id": account_id,
                "token": token,
                "password": password,
                "domain_type": domain_type
            })
        else:
            # For custom/popular domains, just create the email entry
            email = f"{username}@{domain}"
            
            # Store in memory only (no actual email account created)
            dummy_id = str(uuid.uuid4())
            dummy_token = str(uuid.uuid4())
            
            storage.add_account(email, {
                "id": dummy_id,
                "token": dummy_token,
                "password": password,
                "domain_type": domain_type
            })
        
        logger.info(f"Generated new email: {email}")
        
        return jsonify({
            "email": email,
            "password": password,
            "domain_type": domain_type,
            "message": "Temporary email created successfully"
        }), 201
        
    except requests.RequestException as e:
        logger.error(f"Error connecting to Mail.tm API: {str(e)}")
        return jsonify({"error": "Error connecting to email service"}), 503
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@api_bp.route('/emails/<email_address>', methods=['GET'])
def get_emails(email_address):
    """Get all emails for a specific temporary email address"""
    # Check rate limit
    client_ip = request.remote_addr
    if not rate_limiter.check_rate_limit(client_ip, 'get_emails'):
        return jsonify({"error": "Rate limit exceeded"}), 429
    
    try:
        # Get account data
        account_data = storage.get_account(email_address)
        if not account_data:
            return jsonify({"error": "Email address not found"}), 404
        
        # Get emails from Mail.tm
        headers = {"Authorization": f"Bearer {account_data['token']}"}
        response = requests.get(
            f"{MAIL_TM_API_BASE}/messages",
            headers=headers
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch emails: {response.text}")
            return jsonify({"error": "Failed to fetch emails"}), 500
        
        emails_data = response.json()
        
        # Format and save emails
        emails = []
        for email in emails_data.get('hydra:member', []):
            # Save email to database
            storage.save_email(email_address, email)
            
            # Add to response list
            emails.append({
                "id": email.get('id'),
                "from": email.get('from', {}).get('address'),
                "subject": email.get('subject'),
                "intro": email.get('intro'),
                "isRead": email.get('seen', False),
                "createdAt": email.get('createdAt')
            })
        
        # Get emails from database as a fallback
        if not emails:
            emails = storage.get_emails(email_address)
        
        return jsonify({
            "email": email_address,
            "messages": emails
        }), 200
        
    except requests.RequestException as e:
        logger.error(f"Error connecting to Mail.tm API: {str(e)}")
        return jsonify({"error": "Error connecting to email service"}), 503
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@api_bp.route('/emails/<email_address>/<message_id>', methods=['GET'])
def get_email_content(email_address, message_id):
    """Get content of a specific email"""
    # Check rate limit
    client_ip = request.remote_addr
    if not rate_limiter.check_rate_limit(client_ip, 'get_email_content'):
        return jsonify({"error": "Rate limit exceeded"}), 429
    
    try:
        # First try to get email from database
        db_email = storage.get_email(email_address, message_id)
        if db_email:
            # Mark as read in database
            storage.mark_email_as_read(email_address, message_id)
            return jsonify(db_email), 200
        
        # If not in database, get account data and fetch from API
        account_data = storage.get_account(email_address)
        if not account_data:
            return jsonify({"error": "Email address not found"}), 404
        
        # Get email content from Mail.tm
        headers = {"Authorization": f"Bearer {account_data['token']}"}
        response = requests.get(
            f"{MAIL_TM_API_BASE}/messages/{message_id}",
            headers=headers
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch email content: {response.text}")
            return jsonify({"error": "Failed to fetch email content"}), 500
        
        email_data = response.json()
        
        # Mark as read
        requests.patch(
            f"{MAIL_TM_API_BASE}/messages/{message_id}",
            headers=headers,
            json={"seen": True}
        )
        
        # Save complete email to database
        storage.save_email(email_address, email_data)
        
        # Format and return the email content
        email_content = {
            "id": email_data.get('id'),
            "from": email_data.get('from', {}).get('address'),
            "to": email_data.get('to', [{}])[0].get('address'),
            "subject": email_data.get('subject'),
            "text": email_data.get('text'),
            "html": email_data.get('html'),
            "attachments": email_data.get('attachments', []),
            "createdAt": email_data.get('createdAt')
        }
        
        return jsonify(email_content), 200
        
    except requests.RequestException as e:
        logger.error(f"Error connecting to Mail.tm API: {str(e)}")
        return jsonify({"error": "Error connecting to email service"}), 503
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@api_bp.route('/emails/<email_address>/<message_id>', methods=['DELETE'])
def delete_email(email_address, message_id):
    """Delete a specific email"""
    # Check rate limit
    client_ip = request.remote_addr
    if not rate_limiter.check_rate_limit(client_ip, 'delete_email'):
        return jsonify({"error": "Rate limit exceeded"}), 429
    
    try:
        # Get account data
        account_data = storage.get_account(email_address)
        if not account_data:
            return jsonify({"error": "Email address not found"}), 404
        
        # Delete email from Mail.tm
        headers = {"Authorization": f"Bearer {account_data['token']}"}
        response = requests.delete(
            f"{MAIL_TM_API_BASE}/messages/{message_id}",
            headers=headers
        )
        
        if response.status_code != 204:
            logger.error(f"Failed to delete email: {response.text}")
            return jsonify({"error": "Failed to delete email"}), 500
        
        # Also delete from database
        storage.delete_email(email_address, message_id)
        
        return jsonify({
            "message": "Email deleted successfully"
        }), 200
        
    except requests.RequestException as e:
        logger.error(f"Error connecting to Mail.tm API: {str(e)}")
        return jsonify({"error": "Error connecting to email service"}), 503
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@api_bp.route('/delete/<email_address>', methods=['DELETE'])
def delete_account(email_address):
    """Delete a temporary email account"""
    # Check rate limit
    client_ip = request.remote_addr
    if not rate_limiter.check_rate_limit(client_ip, 'delete_account'):
        return jsonify({"error": "Rate limit exceeded"}), 429
    
    try:
        # Get account data
        account_data = storage.get_account(email_address)
        if not account_data:
            return jsonify({"error": "Email address not found"}), 404
        
        # Delete account from Mail.tm
        headers = {"Authorization": f"Bearer {account_data['token']}"}
        response = requests.delete(
            f"{MAIL_TM_API_BASE}/accounts/{account_data['id']}",
            headers=headers
        )
        
        if response.status_code != 204:
            logger.error(f"Failed to delete account: {response.text}")
            return jsonify({"error": "Failed to delete account"}), 500
        
        # Remove from storage
        storage.remove_account(email_address)
        
        return jsonify({
            "message": "Email account deleted successfully"
        }), 200
        
    except requests.RequestException as e:
        logger.error(f"Error connecting to Mail.tm API: {str(e)}")
        return jsonify({"error": "Error connecting to email service"}), 503
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

def register_api_routes(app):
    """Register API routes with the Flask app"""
    app.register_blueprint(api_bp)
