#!/bin/bash

# Create uploads directory if it doesn't exist
mkdir -p uploads

# Initialize the database
python -c "from app import init_db; init_db()"

# Start the Flask application with Gunicorn
gunicorn --bind 0.0.0.0:8000 --workers 4 --timeout 300 app:app
