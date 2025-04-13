import os
import logging
from flask import Flask, render_template, jsonify
from api import register_api_routes
from models import db
from domain_manager import DomainManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "temporary_secret_key_for_dev")

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize database and domain manager
db.init_app(app)
domain_manager = DomainManager()

# Create tables
with app.app_context():
    # Drop and recreate tables (only during development)
    db.drop_all()
    db.create_all()
    logger.info("Database tables created")
    
    # Initialize domain manager
    domain_manager.init_app(app)

# Register API routes
register_api_routes(app)

# Web interface routes
@app.route('/')
def index():
    """Render the main page with API documentation."""
    return render_template('index.html')

@app.route('/documentation')
def documentation():
    """Render the API documentation page."""
    return render_template('documentation.html')

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
