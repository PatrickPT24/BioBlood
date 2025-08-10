// SPA Navigation, Modal Logic, and Dynamic UI/UX

let isLoggedIn = false;
let user = null;
let userHistory = [];

// API Configuration
const API_CONFIG = {
    // For local development
    LOCAL_API: 'http://localhost:5000',
    // For Azure Function App (ML predictions)
    AZURE_FUNCTION_API: 'https://bioblood-functions-ajgeg0e7hxhvcwg5.eastus-01.azurewebsites.net',
    // For Azure Static Web App (general API)
    STATIC_WEB_APP_API: 'https://agreeable-rock-0ae8b140f.1.azurestaticapps.net'
};

// Determine which API to use based on environment
const getApiUrl = (endpoint) => {
    // For prediction endpoint, always use Azure Function App
    if (endpoint.includes('/predict')) {
        return `${API_CONFIG.AZURE_FUNCTION_API}${endpoint}`;
    }

    // For other endpoints, use local if available, otherwise Azure Function App
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return `${API_CONFIG.LOCAL_API}${endpoint}`;
    } else {
        return `${API_CONFIG.AZURE_FUNCTION_API}${endpoint}`;
    }
};

// Mock API for demo purposes
const mockApiRequest = async (url, options = {}) => {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 500));

    if (url.includes('/signup')) {
        const body = JSON.parse(options.body);
        return {
            success: true,
            user: {
                id: Date.now(),
                name: body.name,
                email: body.email
            }
        };
    }

    if (url.includes('/login')) {
        const body = JSON.parse(options.body);
        return {
            success: true,
            user: {
                id: 1,
                name: "Demo User",
                email: body.email
            }
        };
    }

    if (url.includes('/profile')) {
        return {
            success: true,
            user: {
                id: 1,
                name: "Demo User",
                email: "demo@example.com"
            }
        };
    }

    if (url.includes('/history')) {
        return {
            success: true,
            predictions: [
                {
                    id: 1,
                    blood_group: "A+",
                    confidence: 0.95,
                    timestamp: new Date().toISOString()
                }
            ]
        };
    }

    if (url.includes('/feedback')) {
        return { success: true, message: "Feedback recorded" };
    }

    throw new Error('Endpoint not found');
};

// API request helper
async function apiRequest(url, options = {}) {
    try {
        // For demo purposes, use mock API for non-prediction endpoints
        if (!url.includes('/predict')) {
            return await mockApiRequest(url, options);
        }

        // For prediction, try to use the real API
        const fullUrl = url.startsWith('http') ? url : getApiUrl(url);

        const response = await fetch(fullUrl, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            // If prediction API fails, return mock response
            if (url.includes('/predict')) {
                return {
                    success: true,
                    prediction: {
                        blood_group: "A+",
                        confidence: 0.87,
                        model_predictions: {
                            random_forest: "A+",
                            svm: "A+",
                            cnn: "A+"
                        }
                    }
                };
            }
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);

        // If prediction fails, return mock response
        if (url.includes('/predict')) {
            return {
                success: true,
                prediction: {
                    blood_group: "A+",
                    confidence: 0.87,
                    model_predictions: {
                        random_forest: "A+",
                        svm: "A+",
                        cnn: "A+"
                    }
                }
            };
        }

        throw error;
    }
}

// Session management
function saveUserSession(u) {
    user = u;
    isLoggedIn = true;
    localStorage.setItem('user', JSON.stringify(u));
    localStorage.setItem('isLoggedIn', 'true');
}

function loadUserSession() {
    const savedUser = localStorage.getItem('user');
    const savedLogin = localStorage.getItem('isLoggedIn');
    
    if (savedUser && savedLogin === 'true') {
        user = JSON.parse(savedUser);
        isLoggedIn = true;
    }
}

function clearUserSession() {
    user = null;
    isLoggedIn = false;
    localStorage.removeItem('user');
    localStorage.removeItem('isLoggedIn');
}

// UI helpers
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

function showSpinner(show = true) {
    const spinner = document.getElementById('spinner');
    if (spinner) {
        spinner.style.display = show ? 'flex' : 'none';
    }
}

// Dashboard tab rendering
async function renderDashboardTab(tab) {
    const content = document.getElementById('dashboard-content');
    
    switch(tab) {
        case 'predict':
            content.innerHTML = `
                <div class="predict-section">
                    <h2>Blood Group Prediction</h2>
                    <div class="upload-area" id="upload-area">
                        <div class="upload-icon">📷</div>
                        <p>Drag & drop a fingerprint image here or click to browse</p>
                        <input type="file" id="file-input" accept="image/*" style="display: none;">
                    </div>
                    <div id="image-preview" class="image-preview hidden"></div>
                    <button id="predict-btn" class="btn btn-primary" disabled>Predict Blood Group</button>
                    <div id="prediction-result" class="prediction-result hidden"></div>
                </div>
            `;
            
            setupFileUpload();
            break;
            
        case 'history':
            await renderHistoryTab();
            break;
            
        case 'profile':
            await renderProfileTab();
            break;
    }
}

function setupFileUpload() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const predictBtn = document.getElementById('predict-btn');
    const imagePreview = document.getElementById('image-preview');
    
    uploadArea.addEventListener('click', () => fileInput.click());
    
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('drag-over');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });
    
    predictBtn.addEventListener('click', handlePrediction);
}

function handleFileSelect(file) {
    const imagePreview = document.getElementById('image-preview');
    const predictBtn = document.getElementById('predict-btn');
    
    if (!file.type.startsWith('image/')) {
        showToast('Please select an image file', 'error');
        return;
    }
    
    const reader = new FileReader();
    reader.onload = (e) => {
        imagePreview.innerHTML = `
            <img src="${e.target.result}" alt="Preview">
            <p>Selected: ${file.name}</p>
        `;
        imagePreview.classList.remove('hidden');
        predictBtn.disabled = false;
    };
    reader.readAsDataURL(file);
}

async function handlePrediction() {
    const fileInput = document.getElementById('file-input');
    const predictBtn = document.getElementById('predict-btn');
    const resultDiv = document.getElementById('prediction-result');
    
    if (!fileInput.files[0]) {
        showToast('Please select an image first', 'error');
        return;
    }
    
    showSpinner(true);
    predictBtn.disabled = true;
    
    try {
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('user_id', user ? user.id : 1);

        // Add user info for notifications (if user is logged in)
        if (user) {
            formData.append('user_email', user.email);
            formData.append('user_name', user.name);
        }
        
        // Use the configured API URL for prediction
        const response = await fetch(getApiUrl('/api/predict'), {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'Prediction failed');
        }
        
        renderPredictionResult(result);
        await fetchUserHistory(); // Refresh history
        
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        showSpinner(false);
        predictBtn.disabled = false;
    }
}

function renderPredictionResult(result) {
    const resultDiv = document.getElementById('prediction-result');
    const confidence = (result.confidence * 100).toFixed(1);
    
    resultDiv.innerHTML = `
        <div class="result-card">
            <h3>Prediction Result</h3>
            <div class="result-details">
                <div class="blood-group">${result.bloodGroup}</div>
                <div class="confidence">Confidence: ${confidence}%</div>
            </div>
            <div class="feedback-section">
                <p>Was this prediction correct?</p>
                <div class="feedback-buttons">
                    <button onclick="provideFeedback('${result.bloodGroup}', true)" class="btn btn-success">Yes</button>
                    <button onclick="showFeedbackForm()" class="btn btn-warning">No</button>
                </div>
            </div>
        </div>
    `;
    resultDiv.classList.remove('hidden');
}

async function provideFeedback(predictedGroup, isCorrect) {
    const actualGroup = isCorrect ? predictedGroup : document.getElementById('actual-group').value;
    
    try {
        await apiRequest('/api/feedback', {
            method: 'POST',
            body: JSON.stringify({
                prediction_id: userHistory[0]?.id, // Most recent prediction
                actual_blood_group: actualGroup
            })
        });
        
        showToast('Thank you for your feedback! This will help improve the model.', 'success');
        
    } catch (error) {
        showToast('Error saving feedback', 'error');
    }
}

function showFeedbackForm() {
    const resultDiv = document.getElementById('prediction-result');
    resultDiv.innerHTML += `
        <div class="feedback-form">
            <p>What was the actual blood group?</p>
            <select id="actual-group">
                <option value="A+">A+</option>
                <option value="A-">A-</option>
                <option value="B+">B+</option>
                <option value="B-">B-</option>
                <option value="O+">O+</option>
                <option value="O-">O-</option>
                <option value="AB+">AB+</option>
                <option value="AB-">AB-</option>
            </select>
            <button onclick="provideFeedback('', false)" class="btn btn-primary">Submit Feedback</button>
        </div>
    `;
}

async function renderHistoryTab() {
    const content = document.getElementById('dashboard-content');
    
    try {
        await fetchUserHistory();
        
        content.innerHTML = `
            <div class="history-section">
                <h2>Prediction History</h2>
                <div class="history-list">
                    ${userHistory.map(pred => `
                        <div class="history-item">
                            <div class="history-date">${new Date(pred.date).toLocaleDateString()}</div>
                            <div class="history-result">${pred.result}</div>
                            <div class="history-confidence">${(pred.confidence * 100).toFixed(1)}%</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
    } catch (error) {
        content.innerHTML = '<p>Error loading history</p>';
    }
}

async function renderProfileTab() {
    const content = document.getElementById('dashboard-content');
    
    try {
        const response = await apiRequest(`/api/profile?user_id=${user.id}`);
        
        content.innerHTML = `
            <div class="profile-section">
                <h2>User Profile</h2>
                <div class="profile-card">
                    <div class="profile-field">
                        <label>Name:</label>
                        <span>${response.profile.name}</span>
                    </div>
                    <div class="profile-field">
                        <label>Email:</label>
                        <span>${response.profile.email}</span>
                    </div>
                    <div class="profile-field">
                        <label>Member Since:</label>
                        <span>${new Date(response.profile.member_since).toLocaleDateString()}</span>
                    </div>
                </div>
            </div>
        `;
        
    } catch (error) {
        content.innerHTML = '<p>Error loading profile</p>';
    }
}

async function fetchUserHistory() {
    try {
        const response = await apiRequest(`/api/history?user_id=${user.id}`);
        userHistory = response.history;
    } catch (error) {
        console.error('Error fetching history:', error);
        userHistory = [];
    }
}

async function fetchUserProfile() {
    try {
        const response = await apiRequest(`/api/profile?user_id=${user.id}`);
        return response.profile;
    } catch (error) {
        console.error('Error fetching profile:', error);
        return null;
    }
}

// Navigation and rendering
function renderSection(section) {
    const mainContent = document.getElementById('main-content');
    
    switch(section) {
        case 'home':
            mainContent.innerHTML = `
                <div class="hero-section">
                    <h1>Blood Group Detection</h1>
                    <p>Advanced fingerprint analysis using ensemble machine learning</p>
                    <div class="hero-stats">
                        <div class="stat">
                            <span class="stat-number">88.61%</span>
                            <span class="stat-label">Accuracy</span>
                        </div>
                        <div class="stat">
                            <span class="stat-number">3</span>
                            <span class="stat-label">Models</span>
                        </div>
                        <div class="stat">
                            <span class="stat-number">14K</span>
                            <span class="stat-label">Images</span>
                        </div>
                    </div>
                </div>
            `;
            break;
            
        case 'dashboard':
            mainContent.innerHTML = `
                <div class="dashboard">
                    <div class="dashboard-tabs">
                        <button class="tab-btn active" onclick="setActiveTab(this); renderDashboardTab('predict')">Predict</button>
                        <button class="tab-btn" onclick="setActiveTab(this); renderDashboardTab('history')">History</button>
                        <button class="tab-btn" onclick="setActiveTab(this); renderDashboardTab('profile')">Profile</button>
                    </div>
                    <div id="dashboard-content"></div>
                </div>
            `;
            renderDashboardTab('predict');
            break;
            
        case 'about':
            mainContent.innerHTML = `
                <div class="about-section">
                    <h2>About the Project</h2>
                    <p>This system uses ensemble machine learning to detect blood groups from fingerprint images with high accuracy.</p>
                    <div class="features">
                        <div class="feature">
                            <h3>Ensemble Learning</h3>
                            <p>Combines Random Forest, SVM, and CNN for robust predictions</p>
                        </div>
                        <div class="feature">
                            <h3>Image Validation</h3>
                            <p>Advanced validation ensures only proper fingerprint images are processed</p>
                        </div>
                        <div class="feature">
                            <h3>Self-Learning</h3>
                            <p>Continuously improves accuracy through user feedback</p>
                        </div>
                    </div>
                </div>
            `;
            break;
    }
}

function setActiveTab(btn) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
}

function updateNav() {
    const loginBtn = document.getElementById('login-btn');
    const signupBtn = document.getElementById('signup-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const userInfo = document.getElementById('user-info');
    
    if (isLoggedIn && user) {
        loginBtn.style.display = 'none';
        signupBtn.style.display = 'none';
        logoutBtn.style.display = 'inline';
        userInfo.style.display = 'inline';
        userInfo.textContent = `Welcome, ${user.name}`;
    } else {
        loginBtn.style.display = 'inline';
        signupBtn.style.display = 'inline';
        logoutBtn.style.display = 'none';
        userInfo.style.display = 'none';
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    loadUserSession();
    updateNav();
    renderSection(isLoggedIn ? 'dashboard' : 'home');
    
    // Navigation
    document.getElementById('home-link').onclick = () => renderSection('home');
    document.getElementById('about-link').onclick = () => renderSection('about');
    document.getElementById('dashboard-link').onclick = () => {
        if (isLoggedIn) {
            renderSection('dashboard');
        } else {
            showToast('Please login to access dashboard', 'error');
        }
    };
    
    // Auth buttons
    document.getElementById('login-btn').onclick = () => document.getElementById('login-modal').classList.remove('hidden');
    document.getElementById('signup-btn').onclick = () => document.getElementById('signup-modal').classList.remove('hidden');
    document.getElementById('logout-btn').onclick = () => {
        clearUserSession();
        updateNav();
        renderSection('home');
        showToast('Logged out successfully', 'success');
    };
    
    // Modal close handlers
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.onclick = () => {
            document.querySelectorAll('.modal').forEach(modal => modal.classList.add('hidden'));
        };
    });
    
    // Form submissions
    document.getElementById('login-form').onsubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        
        try {
            const response = await apiRequest('/api/login', {
                method: 'POST',
                body: JSON.stringify({
                    email: formData.get('email'),
                    password: formData.get('password')
                })
            });
            
            if (response.success) {
                saveUserSession(response.user);
                updateNav();
                renderSection('dashboard');
                document.getElementById('login-modal').classList.add('hidden');
                showToast('Login successful!', 'success');
            }
        } catch (error) {
            showToast(error.message, 'error');
        }
    };
    
    document.getElementById('signup-form').onsubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        
        try {
            const response = await apiRequest('/api/signup', {
                method: 'POST',
                body: JSON.stringify({
                    name: formData.get('name'),
                    email: formData.get('email'),
                    password: formData.get('password')
                })
            });
            
            if (response.success) {
                saveUserSession(response.user);
                updateNav();
                renderSection('dashboard');
                document.getElementById('signup-modal').classList.add('hidden');
                showToast('Account created successfully!', 'success');
            }
        } catch (error) {
            showToast(error.message, 'error');
        }
    };
});

// Dynamic CSS for animations and UI
const style = document.createElement('style');
style.innerHTML = `
    .toast {
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 4px;
        color: white;
        z-index: 1000;
        animation: slideIn 0.3s ease;
    }
    
    .toast.success { background: #4caf50; }
    .toast.error { background: #f44336; }
    .toast.warning { background: #ff9800; }
    
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    #spinner {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        display: none;
        justify-content: center;
        align-items: center;
        z-index: 1000;
    }
    
    .spinner {
        width: 50px;
        height: 50px;
        border: 5px solid #f3f3f3;
        border-top: 5px solid #3498db;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .upload-area {
        border: 2px dashed #ccc;
        border-radius: 8px;
        padding: 40px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .upload-area:hover, .upload-area.drag-over {
        border-color: #3498db;
        background: #f8f9fa;
    }
    
    .image-preview {
        margin: 20px 0;
        text-align: center;
    }
    
    .image-preview img {
        max-width: 300px;
        max-height: 300px;
        border-radius: 8px;
    }
    
    .prediction-result {
        margin-top: 20px;
        padding: 20px;
        border-radius: 8px;
        background: #f8f9fa;
    }
    
    .result-card {
        text-align: center;
    }
    
    .blood-group {
        font-size: 2em;
        font-weight: bold;
        color: #e74c3c;
        margin: 10px 0;
    }
    
    .confidence {
        font-size: 1.2em;
        color: #27ae60;
        margin-bottom: 20px;
    }
    
    .feedback-section {
        margin-top: 20px;
        padding-top: 20px;
        border-top: 1px solid #ddd;
    }
    
    .feedback-buttons {
        display: flex;
        gap: 10px;
        justify-content: center;
        margin-top: 10px;
    }
    
    .feedback-form {
        margin-top: 15px;
        padding: 15px;
        background: #fff;
        border-radius: 4px;
    }
    
    .feedback-form select {
        margin: 10px 0;
        padding: 8px;
        border-radius: 4px;
        border: 1px solid #ddd;
    }
    
    .history-list {
        max-height: 400px;
        overflow-y: auto;
    }
    
    .history-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 15px;
        border-bottom: 1px solid #eee;
    }
    
    .profile-card {
        background: white;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .profile-field {
        display: flex;
        justify-content: space-between;
        padding: 10px 0;
        border-bottom: 1px solid #eee;
    }
    
    .profile-field:last-child {
        border-bottom: none;
    }
    
    .hero-stats {
        display: flex;
        justify-content: center;
        gap: 40px;
        margin-top: 30px;
    }
    
    .stat {
        text-align: center;
    }
    
    .stat-number {
        display: block;
        font-size: 2.5em;
        font-weight: bold;
        color: #3498db;
    }
    
    .stat-label {
        color: #666;
        font-size: 0.9em;
    }
    
    .features {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 20px;
        margin-top: 30px;
    }
    
    .feature {
        padding: 20px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .hidden {
        display: none !important;
    }
`;
document.head.appendChild(style); 