from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import numpy as np
from PIL import Image
import joblib
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
from scipy.stats import mode
import sqlite3
import cv2
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)

# Database setup
def init_db():
    conn = sqlite3.connect('blood_group.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            member_since TEXT NOT NULL
        )
    ''')
    
    # Predictions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            image_path TEXT,
            predicted_blood_group TEXT,
            confidence REAL,
            actual_blood_group TEXT,
            prediction_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Training data table for self-learning
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS training_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path TEXT,
            actual_blood_group TEXT,
            features TEXT,
            added_date TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Blood group mapping
BLOOD_GROUPS = {'A+': 0, 'A-': 1, 'B+': 2, 'B-': 3, 'O+': 4, 'O-': 5, 'AB+': 6, 'AB-': 7}
INV_BLOOD_GROUPS = {v: k for k, v in BLOOD_GROUPS.items()}
IMG_SIZE = (96, 96)

# Load models at startup
rf = joblib.load('saved_models/random_forest.pkl')
svm = joblib.load('saved_models/svm.pkl')
cnn = load_model('saved_models/cnn_model.h5')

# Image validation function
def validate_fingerprint_image(image):
    """Validate if the uploaded image is a proper fingerprint image"""
    try:
        # Convert to numpy array
        img_array = np.array(image)
        
        # Check image quality metrics
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY) if len(img_array.shape) == 3 else img_array
        
        # 1. Check contrast (fingerprint should have good contrast)
        contrast = np.std(gray)
        if contrast < 30:
            return False, "Image has low contrast. Please upload a clearer fingerprint image."
        
        # 2. Check for ridge patterns (fingerprint characteristic)
        # Apply edge detection
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
        
        if edge_density < 0.01:  # Too few edges
            return False, "No clear fingerprint patterns detected. Please upload a proper fingerprint image."
        
        if edge_density > 0.3:  # Too many edges (noise)
            return False, "Image appears to be too noisy. Please upload a clearer fingerprint image."
        
        # 3. Check image size (should be reasonable)
        if gray.shape[0] < 100 or gray.shape[1] < 100:
            return False, "Image is too small. Please upload a larger fingerprint image."
        
        # 4. Check for uniform areas (fingerprint shouldn't be uniform)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist_norm = hist.flatten() / hist.sum()
        entropy = -np.sum(hist_norm * np.log2(hist_norm + 1e-10))
        
        if entropy < 4.0:  # Too uniform
            return False, "Image appears to be too uniform. Please upload a proper fingerprint image."
        
        return True, "Image validation passed."
        
    except Exception as e:
        return False, f"Error validating image: {str(e)}"

# Preprocessing function (same as training)
def preprocess_image(file):
    img = Image.open(file).convert('L').resize(IMG_SIZE)
    img_arr = img_to_array(img) / 255.0
    img_arr = np.expand_dims(img_arr, axis=0)  # (1, H, W, 1)
    return img_arr

def extract_features(images):
    return images.reshape((images.shape[0], -1))

# Self-learning function
def update_models_with_new_data(image_path, actual_blood_group, features):
    """Add new training data for future model updates"""
    try:
        conn = sqlite3.connect('blood_group.db')
        cursor = conn.cursor()
        
        # Store new training data
        cursor.execute('''
            INSERT INTO training_data (image_path, actual_blood_group, features, added_date)
            VALUES (?, ?, ?, ?)
        ''', (image_path, actual_blood_group, json.dumps(features.tolist()), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        print(f"Added new training data: {actual_blood_group} - {image_path}")
        
    except Exception as e:
        print(f"Error updating training data: {e}")

@app.route('/api/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    user_id = request.form.get('user_id', 1)  # Default to user 1 for now
    
    try:
        # Read and validate image
        img = Image.open(file)
        
        # Validate fingerprint image
        is_valid, message = validate_fingerprint_image(img)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Preprocess image
        img_arr = preprocess_image(file)
        X_feat = extract_features(img_arr)
        
        # Predict with all models
        pred_rf = rf.predict(X_feat)[0]
        pred_svm = svm.predict(X_feat)[0]
        pred_cnn = np.argmax(cnn.predict(img_arr), axis=1)[0]
        
        print(f"Individual predictions - RF: {pred_rf}, SVM: {pred_svm}, CNN: {pred_cnn}")
        
        # Majority voting
        preds = np.array([pred_rf, pred_svm, pred_cnn])
        final_pred, count = mode(preds)
        
        # Handle both scalar and array outputs from mode
        if np.isscalar(final_pred):
            final_pred = final_pred
        else:
            final_pred = final_pred[0]
        if np.isscalar(count):
            confidence = count / 3.0
        else:
            confidence = count[0] / 3.0
            
        print(f"Ensemble prediction: {final_pred}, confidence: {confidence}")
        
        # Save prediction to database
        predicted_blood_group = INV_BLOOD_GROUPS[final_pred]
        
        # Save image and prediction
        image_filename = f"uploads/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        os.makedirs('uploads', exist_ok=True)
        img.save(image_filename)
        
        conn = sqlite3.connect('blood_group.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO predictions (user_id, image_path, predicted_blood_group, confidence, prediction_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, image_filename, predicted_blood_group, confidence, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'bloodGroup': predicted_blood_group,
            'confidence': round(float(confidence), 2),
            'message': 'Prediction successful!'
        })
        
    except Exception as e:
        print(f"Prediction error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    conn = sqlite3.connect('blood_group.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'success': True, 
            'user': {
                'id': user[0],
                'name': user[1],
                'email': user[2],
                'member_since': user[4]
            }
        })
    else:
        return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    
    conn = sqlite3.connect('blood_group.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (name, email, password, member_since)
            VALUES (?, ?, ?, ?)
        ''', (name, email, password, datetime.now().isoformat()))
        
        conn.commit()
        user_id = cursor.lastrowid
        
        conn.close()
        
        return jsonify({
            'success': True,
            'user': {
                'id': user_id,
                'name': name,
                'email': email,
                'member_since': datetime.now().isoformat()
            }
        })
        
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'success': False, 'error': 'Email already exists'}), 400
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def history():
    user_id = request.args.get('user_id', 1)
    
    conn = sqlite3.connect('blood_group.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT predicted_blood_group, confidence, prediction_date, image_path
        FROM predictions 
        WHERE user_id = ? 
        ORDER BY prediction_date DESC
        LIMIT 10
    ''', (user_id,))
    
    predictions = cursor.fetchall()
    conn.close()
    
    history = []
    for pred in predictions:
        history.append({
            'date': pred[2],
            'result': pred[0],
            'confidence': pred[1],
            'image_path': pred[3]
        })
    
    return jsonify({'history': history})

@app.route('/api/profile', methods=['GET'])
def profile():
    user_id = request.args.get('user_id', 1)
    
    conn = sqlite3.connect('blood_group.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT name, email, member_since FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'profile': {
                'name': user[0],
                'email': user[1],
                'member_since': user[2]
            }
        })
    else:
        return jsonify({'error': 'User not found'}), 404

@app.route('/api/feedback', methods=['POST'])
def feedback():
    """Handle user feedback for self-learning"""
    data = request.get_json()
    prediction_id = data.get('prediction_id')
    actual_blood_group = data.get('actual_blood_group')
    
    try:
        conn = sqlite3.connect('blood_group.db')
        cursor = conn.cursor()
        
        # Update prediction with actual blood group
        cursor.execute('''
            UPDATE predictions 
            SET actual_blood_group = ? 
            WHERE id = ?
        ''', (actual_blood_group, prediction_id))
        
        # Get the image path for training data
        cursor.execute('SELECT image_path FROM predictions WHERE id = ?', (prediction_id,))
        result = cursor.fetchone()
        
        if result:
            image_path = result[0]
            # Add to training data for future model updates
            update_models_with_new_data(image_path, actual_blood_group, None)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Feedback recorded for model improvement'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 