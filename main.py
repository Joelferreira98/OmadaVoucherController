#!/usr/bin/env python3
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set up environment for production
if 'gunicorn' in os.environ.get('SERVER_SOFTWARE', ''):
    logger.info("Running under Gunicorn")
else:
    logger.info("Running in development mode")

try:
    # Import the Flask app
    from app import app
    
    # Import routes to register them
    import routes
    
    # Ensure the app is available for Gunicorn
    logger.info("Flask app imported successfully")
    
    # For Gunicorn, we need to expose the app object
    application = app
    
    if __name__ == "__main__":
        logger.info("Starting Flask development server...")
        app.run(host="0.0.0.0", port=5000, debug=True)
        
except Exception as e:
    logger.error(f"Error importing Flask app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
