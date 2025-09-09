#!/usr/bin/env python3
"""
Azure App Service startup script
This script ensures proper initialization for Azure deployment
"""

import os
import sys
import logging

# Configure logging for Azure
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set environment variables for Azure
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('PYTHONPATH', '/home/site/wwwroot')

# Set additional environment variables for Azure Linux App Service
os.environ.setdefault('WEBSITES_ENABLE_APP_SERVICE_STORAGE', 'false')
os.environ.setdefault('WEBSITES_PORT', '8000')

# Import the Flask app
from app import app

# Make sure the app object is available for gunicorn
# This is required for the Procfile to work