"""
Blood Group Detection Backend API - Azure Optimized Version
Works with Flask + Azure App Service
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import logging
import traceback
import io
import base64
import hashlib
from datetime import datetime
import threading
import time

# =====================================================
# Initialize Flask app
# =====================================================
app = Flask(__name__)
CORS(app)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =====================================================
# Global Variables
# =====================================================
ensemble_model = None
individual_models = {}
label_encoder = None
blood_groups = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']

# Model loading status
models_loading = False
models_loaded = False

# Model storage for Flask app
app_models = {
    'ensemble_model': None,
    'individual_models': {},
    'label_encoder': None,
    'models_loaded': False
}

# In-memory storage for demo purposes (in production, use a database)
user_predictions = {}
user_profiles = {}

def initialize_sample_data():
    """Initialize some sample data for demo purposes"""
    global user_predictions
    
    # Add some sample predictions for user 2 (default demo user)
    sample_predictions = [
        {
            'prediction_id': 'sample_001',
            'predicted_blood_group': 'A+',
            'confidence': 0.85,
            'model_used': 'Enhanced Ensemble',
            'prediction_date': '2024-09-08 10:30:00',
            'probabilities': {'A+': 0.85, 'A-': 0.05, 'B+': 0.03, 'B-': 0.02, 'O+': 0.02, 'O-': 0.01, 'AB+': 0.01, 'AB-': 0.01},
            'feedback': {
                'actual_blood_group': 'A+',
                'is_correct': True,
                'feedback_date': '2024-09-08 10:35:00'
            }
        },
        {
            'prediction_id': 'sample_002',
            'predicted_blood_group': 'B-',
            'confidence': 0.72,
            'model_used': 'Enhanced Ensemble',
            'prediction_date': '2024-09-08 11:15:00',
            'probabilities': {'A+': 0.05, 'A-': 0.03, 'B+': 0.15, 'B-': 0.72, 'O+': 0.02, 'O-': 0.01, 'AB+': 0.01, 'AB-': 0.01},
            'feedback': {
                'actual_blood_group': 'B+',
                'is_correct': False,
                'feedback_date': '2024-09-08 11:20:00'
            }
        },
        {
            'prediction_id': 'sample_003',
            'predicted_blood_group': 'O+',
            'confidence': 0.91,
            'model_used': 'Enhanced Ensemble',
            'prediction_date': '2024-09-08 14:45:00',
            'probabilities': {'A+': 0.02, 'A-': 0.01, 'B+': 0.02, 'B-': 0.01, 'O+': 0.91, 'O-': 0.02, 'AB+': 0.005, 'AB-': 0.005},
            'feedback': {
                'actual_blood_group': 'O+',
                'is_correct': True,
                'feedback_date': '2024-09-08 14:50:00'
            }
        },
        {
            'prediction_id': 'sample_004',
            'predicted_blood_group': 'AB+',
            'confidence': 0.68,
            'model_used': 'Enhanced Ensemble',
            'prediction_date': '2024-09-08 16:20:00',
            'probabilities': {'A+': 0.15, 'A-': 0.05, 'B+': 0.10, 'B-': 0.02, 'O+': 0.05, 'O-': 0.02, 'AB+': 0.68, 'AB-': 0.03},
            'feedback': None
        }
    ]
    
    user_predictions['2'] = sample_predictions
    user_predictions['4'] = sample_predictions  # Also add for user 4 (default frontend user)
    logger.info("✅ Sample data initialized for demo users")

# Frontend directory
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

# =====================================================
# ML Libraries - Deferred Loading
# =====================================================
ML_LIBRARIES_AVAILABLE = False
np = None
cv2 = None
Image = None
plt = None
joblib = None
keras = None

def load_ml_libraries():
    """Load ML libraries on demand"""
    global ML_LIBRARIES_AVAILABLE, np, cv2, Image, plt, joblib, keras
    
    if ML_LIBRARIES_AVAILABLE:
        return True
        
    try:
        import numpy as np
        import cv2
        from PIL import Image
        import matplotlib.pyplot as plt
        import joblib
        import keras
        
        ML_LIBRARIES_AVAILABLE = True
        logger.info("✅ ML libraries loaded successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to load ML libraries: {e}")
        return False

# =====================================================
# Enhanced Ensemble Class
# =====================================================
class EnhancedBloodGroupEnsemble:
    """Enhanced ensemble classifier with automatic weight optimization and multiple strategies"""
    
    def __init__(self, cnn_model, svm_model, rf_model, label_encoder, weights=None, optimize_weights=True):
        self.cnn_model = cnn_model
        self.svm_model = svm_model
        self.rf_model = rf_model
        self.label_encoder = label_encoder
        self.weights = weights or [1/3, 1/3, 1/3]
        self.optimize_weights = optimize_weights
        self.available_models = []
        self.optimized_weights = None
        self.individual_accuracies = {}
        
        # Check which models are available
        if self.cnn_model is not None:
            self.available_models.append('cnn')
        if self.svm_model is not None:
            self.available_models.append('svm')
        if self.rf_model is not None:
            self.available_models.append('rf')
            
        logger.info(f"📊 Available models: {self.available_models}")
        logger.info(f"⚖️  Initial weights: {self.weights}")
    
    def predict_proba(self, X_images, X_features, method='weighted_average'):
        """Get prediction probabilities using different ensemble methods"""
        predictions = []
        model_names = []
        
        # CNN predictions
        if self.cnn_model is not None and X_images is not None:
            # X_images is already in the correct shape (batch, 96, 96, 1)
            cnn_proba = self.cnn_model.predict(X_images, verbose=0)
            predictions.append(cnn_proba)
            model_names.append('cnn')
            logger.info(f"✅ CNN predictions obtained: {cnn_proba.shape}")
        
        # SVM predictions
        if self.svm_model is not None and X_features is not None:
            svm_proba = self.svm_model.predict_proba(X_features)
            predictions.append(svm_proba)
            model_names.append('svm')
            logger.info(f"✅ SVM predictions obtained: {svm_proba.shape}")
        
        # Random Forest predictions
        if self.rf_model is not None and X_features is not None:
            rf_proba = self.rf_model.predict_proba(X_features)
            predictions.append(rf_proba)
            model_names.append('rf')
            logger.info(f"✅ RF predictions obtained: {rf_proba.shape}")
        
        if not predictions:
            raise ValueError("No models available for prediction")
        
        # Use weighted average ensemble
        return self._weighted_average_ensemble(predictions, model_names)
    
    def _weighted_average_ensemble(self, predictions, model_names):
        """Weighted average ensemble with optimized weights"""
        # Map model names to weights
        weight_map = {'cnn': self.weights[0], 'svm': self.weights[1], 'rf': self.weights[2]}
        weights = [weight_map[name] for name in model_names]
        
        # Normalize weights
        weights = np.array(weights)
        weights = weights / np.sum(weights)
        
        weighted_proba = np.zeros_like(predictions[0])
        for i, pred in enumerate(predictions):
            weighted_proba += weights[i] * pred
        
        logger.info(f"📊 Weighted average ensemble (weights: {weights}): {weighted_proba.shape}")
        return weighted_proba
    
    def predict(self, X_images, X_features, method='weighted_average'):
        """Get final predictions"""
        proba = self.predict_proba(X_images, X_features, method=method)
        return np.argmax(proba, axis=1)

# =====================================================
# Model Loading
# =====================================================
def load_models():
    """Load trained models from the models/ directory"""
    global ensemble_model, individual_models, label_encoder, models_loading, models_loaded
    
    models_loading = True
    logger.info("🔄 Starting model loading...")
    
    try:
        # Load ML libraries first
        if not load_ml_libraries():
            logger.error("❌ Cannot load models without ML libraries")
            models_loading = False
            return
            
        model_paths = {
            'ensemble': 'models/enhanced_ensemble_blood_group_model.pkl',
            'cnn': 'models/cnn_blood_group_model.h5',
            'svm': 'models/svm_complete_pipeline.pkl',
            'rf': 'models/rf_blood_group_model.pkl',
            'label_encoder': 'models/label_encoder.pkl'
        }

        # Load enhanced ensemble model first
        if os.path.exists(model_paths['ensemble']):
            try:
                ensemble_model = joblib.load(model_paths['ensemble'])
                logger.info("✅ Enhanced ensemble model loaded")
            except Exception as e:
                logger.error(f"❌ Failed to load enhanced ensemble model: {e}")

        # Load individual models
        cnn_model = None
        svm_model = None
        rf_model = None
        
        for model_name, path in model_paths.items():
            if model_name == 'ensemble':
                continue
            if os.path.exists(path):
                try:
                    if model_name == 'cnn':
                        cnn_model = keras.models.load_model(path)
                        individual_models[model_name] = cnn_model
                    else:
                        model = joblib.load(path)
                        individual_models[model_name] = model
                        if model_name == 'svm':
                            svm_model = model
                        elif model_name == 'rf':
                            rf_model = model
                    logger.info(f"✅ {model_name.upper()} model loaded")
                except Exception as e:
                    logger.error(f"❌ Failed to load {model_name}: {e}")

        # Set label encoder
        if 'label_encoder' in individual_models:
            label_encoder = individual_models['label_encoder']
        elif os.path.exists('models/label_encoder.pkl'):
            try:
                label_encoder = joblib.load('models/label_encoder.pkl')
                logger.info("✅ Label encoder loaded")
            except Exception as e:
                logger.error(f"❌ Failed to load label encoder: {e}")
                # Create a simple one
                from sklearn.preprocessing import LabelEncoder
                label_encoder = LabelEncoder()
                label_encoder.fit(blood_groups)
                logger.info("✅ Fallback label encoder created")
        else:
            logger.info("🔄 Creating label encoder...")
            from sklearn.preprocessing import LabelEncoder
            label_encoder = LabelEncoder()
            label_encoder.fit(blood_groups)
            # Save it for future use
            joblib.dump(label_encoder, 'models/label_encoder.pkl')
            logger.info("✅ Label encoder created and saved")

        # Create ensemble model if we have individual models and no enhanced ensemble loaded
        if ensemble_model is None and (cnn_model is not None or svm_model is not None or rf_model is not None):
            ensemble_model = EnhancedBloodGroupEnsemble(
                cnn_model=cnn_model,
                svm_model=svm_model,
                rf_model=rf_model,
                label_encoder=label_encoder,
                weights=[0.4, 0.3, 0.3]  # CNN gets higher weight
            )
            logger.info("✅ Enhanced ensemble model created from individual models")

        # Store models in app_models for Flask access
        app_models['ensemble_model'] = ensemble_model
        app_models['individual_models'] = individual_models
        app_models['label_encoder'] = label_encoder
        app_models['models_loaded'] = True

        models_loaded = True
        logger.info("✅ All models loaded successfully!")

    except Exception as e:
        logger.error(f"❌ Error loading models: {e}")
        logger.error(traceback.format_exc())
    finally:
        models_loading = False

# =====================================================
# Image Processing
# =====================================================
def preprocess_image(image_data):
    """Preprocess image for prediction"""
    try:
        if not load_ml_libraries():
            raise Exception("ML libraries not available")
            
        # Decode base64 image
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to grayscale for CNN (which expects 1 channel)
        if image.mode != 'L':
            image = image.convert('L')
        
        # Convert to numpy array
        img_array = np.array(image)
        
        # Resize to standard size (CNN expects 96x96)
        img_resized = cv2.resize(img_array, (96, 96))
        
        # Normalize
        img_normalized = img_resized.astype(np.float32) / 255.0
        
        # Add channel dimension for CNN (96, 96) -> (96, 96, 1)
        img_with_channel = np.expand_dims(img_normalized, axis=-1)
        
        # Add batch dimension
        img_batch = np.expand_dims(img_with_channel, axis=0)
        
        return img_batch
        
    except Exception as e:
        logger.error(f"❌ Image preprocessing error: {e}")
        raise Exception(f"Failed to preprocess image: {e}")

def extract_features(image_data):
    """Extract features for traditional ML models"""
    try:
        if not load_ml_libraries():
            raise Exception("ML libraries not available")
            
        # Decode base64 image
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to grayscale for feature extraction
        if image.mode != 'L':
            image = image.convert('L')
        
        # Convert to numpy array
        img_array = np.array(image)
        
        # Resize to standard size
        img_resized = cv2.resize(img_array, (96, 96))
        
        # Extract advanced features (matching training)
        features = []
        
        # Basic statistical features (6)
        features.extend([
            np.mean(img_resized),
            np.std(img_resized),
            np.var(img_resized),
            np.min(img_resized),
            np.max(img_resized),
            np.median(img_resized)
        ])
        
        # Histogram features (32)
        hist, _ = np.histogram(img_resized, bins=32, range=(0, 256))
        hist = hist / np.sum(hist)  # Normalize
        features.extend(hist)
        
        # Local Binary Pattern features (10)
        try:
            from skimage.feature import local_binary_pattern
            lbp = local_binary_pattern(img_resized, P=8, R=1, method='uniform')
            lbp_hist, _ = np.histogram(lbp, bins=10)
            lbp_hist = lbp_hist / np.sum(lbp_hist)
            features.extend(lbp_hist)
        except:
            features.extend([0] * 10)
        
        # GLCM features (16)
        try:
            from skimage.feature import graycomatrix, graycoprops
            glcm = graycomatrix(img_resized.astype(np.uint8), [1], [0, np.pi/4, np.pi/2, 3*np.pi/4], levels=256)
            contrast = graycoprops(glcm, 'contrast').flatten()
            dissimilarity = graycoprops(glcm, 'dissimilarity').flatten()
            homogeneity = graycoprops(glcm, 'homogeneity').flatten()
            energy = graycoprops(glcm, 'energy').flatten()
            features.extend(contrast)
            features.extend(dissimilarity)
            features.extend(homogeneity)
            features.extend(energy)
        except:
            features.extend([0] * 16)
        
        # Gabor filter responses (8)
        try:
            from skimage.filters import gabor
            for theta in [0, 45, 90, 135]:
                filtered, _ = gabor(img_resized, frequency=0.1, theta=np.deg2rad(theta))
                features.extend([np.mean(filtered), np.std(filtered)])
        except:
            features.extend([0] * 8)
        
        # Edge density (1)
        try:
            edges = cv2.Canny(img_resized.astype(np.uint8), 50, 150)
            edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
            features.append(edge_density)
        except:
            features.append(0)
        
        # Convert to numpy array and reshape
        features_array = np.array(features).reshape(1, -1)
        
        return features_array
        
    except Exception as e:
        logger.error(f"❌ Feature extraction error: {e}")
        raise Exception(f"Failed to extract features: {e}")

# =====================================================
# Prediction Functions
# =====================================================
def predict_blood_group(image_data):
    """Predict blood group using ensemble model"""
    try:
        # Use app_models for Flask access
        current_ensemble = app_models.get('ensemble_model')
        current_models_loaded = app_models.get('models_loaded', False)
        
        logger.info(f"🔍 Starting prediction - models_loaded: {current_models_loaded}, ensemble_model: {current_ensemble is not None}")
        
        # Check if models are loaded
        if not current_models_loaded or current_ensemble is None:
            logger.warning("Models not loaded, using fallback prediction")
            return get_fallback_prediction()
            
        logger.info("✅ Models are loaded, proceeding with prediction")
        
        # Preprocess image for CNN
        processed_image = preprocess_image(image_data)
        logger.info(f"✅ Image preprocessed: {processed_image.shape}")
        
        # Extract features for traditional ML models
        features = extract_features(image_data)
        logger.info(f"✅ Features extracted: {features.shape}")
        
        # Use ensemble model if available
        if current_ensemble is not None:
            logger.info("🔍 Getting ensemble predictions...")
            # Get probabilities from ensemble
            probabilities = current_ensemble.predict_proba(processed_image, features)
            probabilities = probabilities[0]  # Get first (and only) prediction
            logger.info(f"✅ Ensemble probabilities: {probabilities}")
            
            # Get blood group with highest probability
            max_idx = np.argmax(probabilities)
            predicted_blood_group = blood_groups[max_idx]
            confidence = float(probabilities[max_idx])
            
            # Create probabilities dict
            prob_dict = {}
            for i, bg in enumerate(blood_groups):
                prob_dict[bg] = float(probabilities[i]) if i < len(probabilities) else 0.0
            
            logger.info(f"✅ Prediction complete: {predicted_blood_group} (confidence: {confidence})")
            
            return {
                'predicted_blood_group': predicted_blood_group,
                'confidence': confidence,
                'probabilities': prob_dict,
                'model_used': 'Enhanced Ensemble',
                'success': True
            }
        else:
            logger.warning("Ensemble model is None, using fallback")
            return get_fallback_prediction()
            
    except Exception as e:
        logger.error(f"❌ Prediction error: {e}")
        logger.error(traceback.format_exc())
        return get_fallback_prediction()

def get_fallback_prediction():
    """Fallback prediction when models are not available"""
    return {
        'predicted_blood_group': 'Unknown',
        'confidence': 0.0,
        'probabilities': {bg: 0.0 for bg in blood_groups},
        'model_used': 'Fallback',
        'success': False,
        'error': 'Models not loaded'
    }

def store_prediction(user_id, prediction_result):
    """Store prediction in memory for demo purposes"""
    global user_predictions
    
    if user_id not in user_predictions:
        user_predictions[user_id] = []
    
    # Add prediction to user's history
    prediction_data = {
        'prediction_id': prediction_result.get('prediction_id', ''),
        'predicted_blood_group': prediction_result.get('predicted_blood_group', ''),
        'confidence': prediction_result.get('confidence', 0.0),
        'model_used': prediction_result.get('model_used', ''),
        'prediction_date': prediction_result.get('timestamp', ''),
        'probabilities': prediction_result.get('probabilities', {}),
        'feedback': None
    }
    
    user_predictions[user_id].append(prediction_data)
    
    # Keep only last 50 predictions per user
    if len(user_predictions[user_id]) > 50:
        user_predictions[user_id] = user_predictions[user_id][-50:]

def get_user_statistics(user_id):
    """Calculate user statistics from prediction history"""
    if user_id not in user_predictions or not user_predictions[user_id]:
        return {
            'total_predictions': 0,
            'accuracy_percentage': 0,
            'most_common_blood_group': 'N/A',
            'feedback_provided': 0,
            'correct_predictions': 0,
            'incorrect_predictions': 0,
            'average_confidence': 0
        }
    
    predictions = user_predictions[user_id]
    total = len(predictions)
    
    # Calculate feedback statistics
    feedback_count = sum(1 for p in predictions if p.get('feedback') is not None)
    correct_count = sum(1 for p in predictions if p.get('feedback') is not None and p.get('feedback', {}).get('is_correct', False))
    incorrect_count = feedback_count - correct_count
    
    # Calculate accuracy
    accuracy = (correct_count / feedback_count * 100) if feedback_count > 0 else 0
    
    # Find most common blood group
    blood_group_counts = {}
    for p in predictions:
        bg = p.get('predicted_blood_group', '')
        blood_group_counts[bg] = blood_group_counts.get(bg, 0) + 1
    
    most_common = max(blood_group_counts.items(), key=lambda x: x[1])[0] if blood_group_counts else 'N/A'
    
    # Calculate average confidence
    avg_confidence = sum(p.get('confidence', 0) for p in predictions) / total * 100 if total > 0 else 0
    
    return {
        'total_predictions': total,
        'accuracy_percentage': round(accuracy, 1),
        'most_common_blood_group': most_common,
        'feedback_provided': feedback_count,
        'correct_predictions': correct_count,
        'incorrect_predictions': incorrect_count,
        'average_confidence': round(avg_confidence, 1)
    }

# =====================================================
# API Routes
# =====================================================

@app.route('/')
def serve_index():
    """Serve the main HTML file"""
    try:
        return send_from_directory(FRONTEND_DIR, 'index.html')
    except Exception as e:
        logger.error(f"Error serving index: {e}")
        return jsonify({'error': 'Frontend not available'}), 500

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    try:
        return send_from_directory(FRONTEND_DIR, filename)
    except Exception as e:
        logger.error(f"Error serving {filename}: {e}")
        return jsonify({'error': 'File not found'}), 404

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        if models_loading:
            return jsonify({
                'message': 'Blood Group Detection API is starting...',
                'models': {
                    'cnn_loaded': False,
                    'ensemble_loaded': False,
                    'label_encoder_loaded': False,
                    'rf_loaded': False,
                    'svm_loaded': False
                },
                'models_loaded': False,
                'models_loading': True,
                'status': 'loading'
            })
        elif app_models.get('models_loaded', False):
            current_individual_models = app_models.get('individual_models', {})
            return jsonify({
                'message': 'Blood Group Detection API is running',
                'models': {
                    'cnn_loaded': 'cnn' in current_individual_models and current_individual_models.get('cnn') is not None,
                    'ensemble_loaded': app_models.get('ensemble_model') is not None,
                    'label_encoder_loaded': app_models.get('label_encoder') is not None,
                    'rf_loaded': 'rf' in current_individual_models and current_individual_models.get('rf') is not None,
                    'svm_loaded': 'svm' in current_individual_models and current_individual_models.get('svm') is not None
                },
                'models_loaded': True,
                'models_loading': False,
                'status': 'healthy'
            })
        else:
            return jsonify({
                'message': 'Blood Group Detection API is starting...',
                'models': {
                    'cnn_loaded': False,
                    'ensemble_loaded': False,
                    'label_encoder_loaded': False,
                    'rf_loaded': False,
                    'svm_loaded': False
                },
                'models_loaded': False,
                'models_loading': False,
                'status': 'starting'
            })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/predict', methods=['POST'])
def predict():
    """Predict blood group from image"""
    try:
        logger.info(f"🔍 Prediction request received - Content-Type: {request.content_type}")
        logger.info(f"🔍 Request method: {request.method}")
        logger.info(f"🔍 Request files: {list(request.files.keys())}")
        logger.info(f"🔍 Request form: {dict(request.form)}")
        logger.info(f"🔍 Request is_json: {request.is_json}")
        
        if models_loading:
            logger.warning("Models are still loading")
            return jsonify({
                'error': 'Models are still loading. Please wait a moment and try again.',
                'success': False
            }), 503
        
        image_data = None
        
        # Check if request contains JSON data (base64 image)
        if request.is_json:
            logger.info("Processing JSON request")
            data = request.get_json()
            if data and 'image' in data:
                image_data = data['image']
                logger.info("Image data found in JSON")
        
        # Check if request contains file upload (FormData)
        elif 'file' in request.files:
            logger.info("Processing file upload request")
            file = request.files['file']
            if file and file.filename:
                logger.info(f"File received: {file.filename}")
                # Read file and convert to base64
                file_data = file.read()
                image_base64 = base64.b64encode(file_data).decode('utf-8')
                image_data = f"data:image/png;base64,{image_base64}"
                logger.info("File converted to base64")
        
        if not image_data:
            logger.error("No image data provided")
            return jsonify({'error': 'No image data provided', 'success': False}), 400
            
        # Get prediction
        result = predict_blood_group(image_data)
        
        # Add timestamp and prediction ID
        result['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        result['prediction_id'] = hashlib.md5(f"{image_data}{datetime.now()}".encode()).hexdigest()[:12]
        
        # Store prediction for user (if user_id provided)
        user_id = request.form.get('user_id') or request.args.get('user_id')
        if user_id and result.get('success', False):
            store_prediction(user_id, result)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({
            'error': str(e),
            'success': False,
            'predicted_blood_group': 'Unknown',
            'confidence': 0.0
        }), 500

@app.route('/api/visualizations', methods=['POST'])
def create_visualizations():
    """Create dynamic visualization charts"""
    try:
        if not load_ml_libraries():
            return jsonify({'error': 'ML libraries not available'}), 500
            
        data = request.get_json()
        if not data or 'probabilities' not in data:
            return jsonify({'error': 'No probabilities provided'}), 400
            
        probabilities = data['probabilities']
        predicted_blood_group = data.get('predicted_blood_group', '')
        confidence = data.get('confidence', 0.0)
        user_id = data.get('user_id', '2')
        
        # Create multiple visualizations
        visualizations = {}
        
        # 1. Blood Group Probability Chart
        visualizations['blood_group_chart'] = create_probability_chart(probabilities, predicted_blood_group, confidence)
        
        # 2. Model Performance Chart (Bar chart only, no pie chart)
        visualizations['model_accuracy'] = create_model_performance_chart()
        
        # 3. User Statistics Chart (if user_id provided)
        if user_id:
            visualizations['user_statistics'] = create_user_statistics_chart(user_id)
        
        return jsonify({
            **visualizations,
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Visualization error: {e}")
        return jsonify({'error': str(e)}), 500

def create_probability_chart(probabilities, predicted_blood_group, confidence):
    """Create blood group probability chart"""
    fig, ax = plt.subplots(figsize=(20, 12))
    
    blood_groups_list = list(probabilities.keys())
    values = list(probabilities.values())
    
    # Convert to percentages
    values_percent = [v * 100 for v in values]
    confidence_percent = confidence * 100
    
    # Create color scheme
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F']
    
    # Create horizontal bar chart
    bars = ax.barh(blood_groups_list, values_percent, color=colors[:len(blood_groups_list)])
    
    # Highlight the predicted blood group
    if predicted_blood_group in blood_groups_list:
        pred_idx = blood_groups_list.index(predicted_blood_group)
        bars[pred_idx].set_color('#FF4444')
        bars[pred_idx].set_edgecolor('#000000')
        bars[pred_idx].set_linewidth(3)
    
    # Customize chart
    ax.set_xlabel('Probability (%)', fontsize=16, fontweight='bold')
    ax.set_title(f'Blood Group Prediction Probabilities\nPredicted: {predicted_blood_group} (Confidence: {confidence_percent:.1f}%)', 
                fontsize=18, fontweight='bold', pad=25)
    ax.set_xlim(0, 100)
    
    # Add value labels on bars
    for i, (bar, value) in enumerate(zip(bars, values_percent)):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, 
               f'{value:.1f}%', va='center', fontsize=14, fontweight='bold')
    
    # Add confidence indicator
    ax.axvline(x=confidence_percent, color='red', linestyle='--', alpha=0.7, linewidth=3)
    ax.text(confidence_percent + 2, len(blood_groups_list) - 1, f'Confidence: {confidence_percent:.1f}%', 
           fontsize=12, color='red', fontweight='bold')
    
    plt.tight_layout()
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=200, bbox_inches='tight', facecolor='white')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return image_base64

def create_model_performance_chart():
    """Create model performance comparison chart"""
    fig, ax = plt.subplots(1, 1, figsize=(20, 10))
    
    # Model accuracy data
    models = ['CNN', 'SVM', 'Random Forest', 'Ensemble']
    accuracies = [0.85, 0.82, 0.79, 0.89]  # Mock data
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
    
    # Convert to percentages
    accuracies_percent = [acc * 100 for acc in accuracies]
    
    # Bar chart
    bars = ax.bar(models, accuracies_percent, color=colors)
    ax.set_ylabel('Accuracy (%)', fontsize=16, fontweight='bold')
    ax.set_title('Model Performance Comparison', fontsize=18, fontweight='bold')
    ax.set_ylim(0, 100)
    
    # Add value labels
    for bar, acc in zip(bars, accuracies_percent):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                f'{acc:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=14)
    
    # Add grid for better readability
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=200, bbox_inches='tight', facecolor='white')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return image_base64

def create_user_statistics_chart(user_id):
    """Create user statistics chart"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(24, 16))
    
    # Get user statistics
    stats = get_user_statistics(user_id)
    
    # 1. Prediction count over time (mock data)
    dates = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
    counts = [5, 8, 12, 15]  # Mock data
    ax1.plot(dates, counts, marker='o', linewidth=4, markersize=10, color='#FF6B6B')
    ax1.set_title('Predictions Over Time', fontsize=16, fontweight='bold')
    ax1.set_ylabel('Number of Predictions', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='both', which='major', labelsize=12)
    
    # 2. Accuracy pie chart
    correct = stats['correct_predictions']
    incorrect = stats['incorrect_predictions']
    if correct + incorrect > 0:
        ax2.pie([correct, incorrect], labels=['Correct', 'Incorrect'], 
               colors=['#4ECDC4', '#FF6B6B'], autopct='%1.1f%%', startangle=90,
               textprops={'fontsize': 14, 'fontweight': 'bold'})
    else:
        ax2.text(0.5, 0.5, 'No feedback data', ha='center', va='center', 
                transform=ax2.transAxes, fontsize=14, fontweight='bold')
    ax2.set_title('Prediction Accuracy', fontsize=16, fontweight='bold')
    
    # 3. Confidence distribution (convert to percentages)
    confidences = [60, 70, 80, 90, 95]  # Mock data in percentages
    counts_conf = [2, 5, 8, 3, 1]  # Mock data
    ax3.bar(confidences, counts_conf, color='#45B7D1', alpha=0.7)
    ax3.set_title('Confidence Distribution', fontsize=16, fontweight='bold')
    ax3.set_xlabel('Confidence Level (%)', fontsize=14, fontweight='bold')
    ax3.set_ylabel('Count', fontsize=14, fontweight='bold')
    ax3.tick_params(axis='both', which='major', labelsize=12)
    
    # 4. Blood group distribution
    bg_data = stats.get('blood_group_distribution', {})
    if bg_data:
        bgs = list(bg_data.keys())
        counts_bg = list(bg_data.values())
        ax4.bar(bgs, counts_bg, color='#96CEB4')
    else:
        ax4.text(0.5, 0.5, 'No blood group data', ha='center', va='center', 
                transform=ax4.transAxes, fontsize=14, fontweight='bold')
    ax4.set_title('Blood Group Distribution', fontsize=16, fontweight='bold')
    ax4.set_ylabel('Count', fontsize=14, fontweight='bold')
    ax4.tick_params(axis='both', which='major', labelsize=12)
    
    plt.suptitle(f'User {user_id} Statistics Dashboard', fontsize=20, fontweight='bold')
    plt.tight_layout()
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=200, bbox_inches='tight', facecolor='white')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return image_base64

def create_blood_group_distribution_chart(user_id):
    """Create blood group distribution chart"""
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Get user's blood group distribution
    if user_id in user_predictions and user_predictions[user_id]:
        bg_counts = {}
        for pred in user_predictions[user_id]:
            bg = pred.get('predicted_blood_group', '')
            bg_counts[bg] = bg_counts.get(bg, 0) + 1
        
        if bg_counts:
            bgs = list(bg_counts.keys())
            counts = list(bg_counts.values())
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F']
            
            wedges, texts, autotexts = ax.pie(counts, labels=bgs, colors=colors[:len(bgs)], 
                                            autopct='%1.1f%%', startangle=90)
            
            # Make percentage text bold
            for autotext in autotexts:
                autotext.set_fontweight('bold')
                autotext.set_fontsize(10)
        else:
            ax.text(0.5, 0.5, 'No prediction data available', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=14)
    else:
        ax.text(0.5, 0.5, 'No prediction data available', ha='center', va='center', 
               transform=ax.transAxes, fontsize=14)
    
    ax.set_title('Your Blood Group Distribution', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=200, bbox_inches='tight', facecolor='white')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return image_base64

def create_confidence_trend_chart(user_id):
    """Create confidence trend chart"""
    fig, ax = plt.subplots(figsize=(16, 8))
    
    if user_id in user_predictions and user_predictions[user_id]:
        predictions = user_predictions[user_id]
        
        # Sort by date
        predictions.sort(key=lambda x: x.get('prediction_date', ''))
        
        # Extract confidence values
        confidences = [p.get('confidence', 0) for p in predictions]
        dates = [f"Pred {i+1}" for i in range(len(confidences))]
        
        # Create line plot
        ax.plot(dates, confidences, marker='o', linewidth=2, markersize=6, color='#FF6B6B')
        ax.fill_between(dates, confidences, alpha=0.3, color='#FF6B6B')
        
        # Add average line
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        ax.axhline(y=avg_confidence, color='blue', linestyle='--', alpha=0.7, 
                  label=f'Average: {avg_confidence:.2f}')
        
        ax.set_title('Confidence Trend Over Time', fontsize=14, fontweight='bold')
        ax.set_ylabel('Confidence Level')
        ax.set_xlabel('Prediction Number')
        ax.set_ylim(0, 1)
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Rotate x-axis labels if too many
        if len(dates) > 10:
            plt.xticks(rotation=45)
    else:
        ax.text(0.5, 0.5, 'No prediction data available', ha='center', va='center', 
               transform=ax.transAxes, fontsize=14)
    
    plt.tight_layout()
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=200, bbox_inches='tight', facecolor='white')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return image_base64

@app.route('/api/profile', methods=['GET'])
def get_profile():
    """Get user profile"""
    try:
        user_id = request.args.get('user_id', '2')
        
        # Get user statistics from prediction history
        statistics = get_user_statistics(user_id)
        
        # Get model usage statistics
        model_usage = {}
        blood_group_distribution = {}
        recent_predictions = []
        
        if user_id in user_predictions and user_predictions[user_id]:
            predictions = user_predictions[user_id]
            
            # Calculate model usage
            for pred in predictions:
                model = pred.get('model_used', 'Unknown')
                model_usage[model] = model_usage.get(model, 0) + 1
            
            # Calculate blood group distribution
            for pred in predictions:
                bg = pred.get('predicted_blood_group', 'Unknown')
                blood_group_distribution[bg] = blood_group_distribution.get(bg, 0) + 1
            
            # Get recent predictions (last 5)
            recent_predictions = predictions[-5:]
        
        # Create comprehensive profile data
        profile_data = {
            'user_id': user_id,
            'name': f'User {user_id}',
            'email': f'user{user_id}@example.com',
            'member_since': '2024-01-15',
            'statistics': statistics,
            'model_usage': model_usage,
            'blood_group_distribution': blood_group_distribution,
            'recent_predictions': recent_predictions
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
        user_id = request.args.get('user_id', '2')
        
        # Get prediction history from stored data
        predictions = user_predictions.get(user_id, [])
        
        # Sort by date (most recent first)
        predictions.sort(key=lambda x: x.get('prediction_date', ''), reverse=True)
        
        return jsonify({
            'success': True,
            'predictions': predictions
        })
    except Exception as e:
        logger.error(f"Predictions error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit feedback"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        prediction_id = data.get('prediction_id')
        actual_blood_group = data.get('actual_blood_group')
        user_id = data.get('user_id')
        
        if not all([prediction_id, actual_blood_group, user_id]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Find and update the prediction with feedback
        if user_id in user_predictions:
            for prediction in user_predictions[user_id]:
                if prediction.get('prediction_id') == prediction_id:
                    predicted_bg = prediction.get('predicted_blood_group', '')
                    is_correct = predicted_bg == actual_blood_group
                    
                    prediction['feedback'] = {
                        'actual_blood_group': actual_blood_group,
                        'is_correct': is_correct,
                        'feedback_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    break
        
        logger.info(f"Feedback received: {data}")
        
        return jsonify({
            'success': True,
            'message': 'Feedback saved successfully'
        })
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        return jsonify({'error': str(e)}), 500

# =====================================================
# Startup
# =====================================================
logger.info("🔄 Initializing Blood Group Detection API...")

# Initialize sample data for demo
initialize_sample_data()

# Azure-optimized model loading strategy
logger.info("🔄 Starting Azure-optimized model loading...")

def load_models_azure_safe():
    """Load models with Azure-specific optimizations"""
    global models_loaded, models_loading
    try:
        logger.info("🔄 Starting background model loading...")
        models_loading = True
        
        # Load models with timeout protection
        load_models()
        
        if models_loaded:
            logger.info("✅ All models loaded successfully!")
        else:
            logger.warning("⚠️  Some models failed to load")
            
    except Exception as e:
        logger.error(f"❌ Model loading failed: {e}")
        logger.error(f"❌ Error details: {str(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
    finally:
        models_loading = False

# Start model loading in background thread with delay
import threading
import time

def delayed_azure_model_loading():
    """Delayed model loading for Azure compatibility"""
    time.sleep(10)  # Wait for app to fully start
    load_models_azure_safe()

# Start background model loading
model_thread = threading.Thread(target=delayed_azure_model_loading, daemon=True)
model_thread.start()

logger.info("✅ API started - Models loading in background for Azure compatibility...")

# =====================================================
# Azure App Service Configuration
# =====================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)

# For Azure App Service - make app available for gunicorn
application = app
