"""
Minimal BioFinger App for Azure Deployment Testing
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Global variables
models_loaded = False
models_loading = False

@app.route('/')
def serve_index():
    """Serve the main HTML file"""
    try:
        return send_from_directory('frontend', 'index.html')
    except Exception as e:
        logger.error(f"Error serving index: {e}")
        return jsonify({'error': 'Frontend not available'}), 500

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    try:
        return send_from_directory('frontend', filename)
    except Exception as e:
        logger.error(f"Error serving {filename}: {e}")
        return jsonify({'error': 'File not found'}), 404

@app.route('/health', methods=['GET'])
def azure_health():
    """Simple health check for Azure liveness probe"""
    return jsonify({'status': 'ok', 'azure_ready': True}), 200

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        return jsonify({
            'message': 'BioFinger API is running (Minimal Version)',
            'status': 'healthy' if models_loaded else 'starting',
            'models_loaded': models_loaded,
            'models_loading': models_loading,
            'azure_ready': True,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({'error': str(e), 'azure_ready': False}), 500

@app.route('/api/profile', methods=['GET'])
def get_profile():
    """Get user profile"""
    try:
        user_id = request.args.get('user_id', '1')
        
        # Sample profile data
        profile_data = {
            'user_id': user_id,
            'name': f'User {user_id}',
            'email': f'user{user_id}@example.com',
            'member_since': '2024-01-15',
            'statistics': {
                'total_predictions': 0,
                'accuracy_percentage': 0,
                'most_common_blood_group': 'N/A',
                'feedback_provided': 0,
                'correct_predictions': 0,
                'incorrect_predictions': 0,
                'average_confidence': 0
            }
        }
        
        return jsonify({
            'success': True,
            'profile': profile_data
        })
    except Exception as e:
        logger.error(f"Profile error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/predictions', methods=['GET'])
def get_predictions():
    """Get prediction history"""
    try:
        user_id = request.args.get('user_id', '1')
        
        # Sample prediction data
        sample_predictions = [
            {
                'prediction_id': 'sample_001',
                'predicted_blood_group': 'A+',
                'confidence': 0.85,
                'model_used': 'Demo Model',
                'prediction_date': '2024-09-09 10:30:00',
                'probabilities': {'A+': 0.85, 'A-': 0.05, 'B+': 0.03, 'B-': 0.02, 'O+': 0.02, 'O-': 0.01, 'AB+': 0.01, 'AB-': 0.01}
            }
        ]
        
        return jsonify({
            'success': True,
            'predictions': sample_predictions
        })
    except Exception as e:
        logger.error(f"Predictions error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("🚀 Starting Minimal BioFinger API...")
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)

# For Azure App Service - make app available for gunicorn
application = app
