# Azure Logic App Setup for BioBlood

## Overview
This Logic App will:
1. Trigger when a prediction is made
2. Send email notifications with prediction results
3. Log predictions to a database/storage
4. Optionally integrate with other systems

## Step 1: Create Logic App

1. Go to Azure Portal → Create a resource
2. Search for "Logic App" → Create
3. Fill in details:
   - **Resource Group**: `bioblood-rg`
   - **Logic App name**: `bioblood-notifications`
   - **Region**: Same as other resources
   - **Plan type**: Consumption
4. Click "Review + Create" → Create

## Step 2: Design the Logic App Workflow

### Trigger: HTTP Request
1. Open Logic App Designer
2. Choose "When a HTTP request is received" trigger
3. Use this JSON schema for the request body:

```json
{
    "type": "object",
    "properties": {
        "userId": {
            "type": "string"
        },
        "bloodGroup": {
            "type": "string"
        },
        "confidence": {
            "type": "number"
        },
        "timestamp": {
            "type": "string"
        },
        "userEmail": {
            "type": "string"
        },
        "userName": {
            "type": "string"
        }
    }
}
```

### Action 1: Send Email Notification
1. Add new step → Choose "Office 365 Outlook" or "Gmail"
2. Sign in to your email account
3. Choose "Send an email (V2)"
4. Configure:
   - **To**: Use dynamic content `userEmail`
   - **Subject**: `BioBlood Prediction Result - @{triggerBody()?['bloodGroup']}`
   - **Body**: 
   ```html
   <h2>BioBlood Prediction Results</h2>
   <p>Hello @{triggerBody()?['userName']},</p>
   <p>Your fingerprint analysis is complete!</p>
   
   <div style="background-color: #f0f8ff; padding: 15px; border-radius: 5px;">
       <h3>Results:</h3>
       <p><strong>Blood Group:</strong> @{triggerBody()?['bloodGroup']}</p>
       <p><strong>Confidence:</strong> @{mul(triggerBody()?['confidence'], 100)}%</p>
       <p><strong>Analysis Time:</strong> @{triggerBody()?['timestamp']}</p>
   </div>
   
   <p>Thank you for using BioBlood!</p>
   <p><em>This is an automated message from the BioBlood system.</em></p>
   ```

### Action 2: Log to Storage (Optional)
1. Add new step → Choose "Azure Blob Storage"
2. Choose "Create blob"
3. Configure:
   - **Storage account**: `biobloodstorage1234`
   - **Container**: `logs`
   - **Blob name**: `prediction-@{utcNow('yyyy-MM-dd-HH-mm-ss')}.json`
   - **Blob content**: 
   ```json
   {
       "userId": "@{triggerBody()?['userId']}",
       "bloodGroup": "@{triggerBody()?['bloodGroup']}",
       "confidence": "@{triggerBody()?['confidence']}",
       "timestamp": "@{triggerBody()?['timestamp']}",
       "userEmail": "@{triggerBody()?['userEmail']}",
       "userName": "@{triggerBody()?['userName']}"
   }
   ```

### Action 3: Response
1. Add new step → Choose "Response"
2. Configure:
   - **Status Code**: 200
   - **Body**: 
   ```json
   {
       "status": "success",
       "message": "Notification sent successfully"
   }
   ```

## Step 3: Get Logic App URL

1. Save the Logic App
2. Copy the HTTP POST URL from the trigger
3. This URL will be used in your Function App

## Step 4: Update Function App to Call Logic App

Add this code to your Function App after successful prediction:

```python
import requests

# Logic App URL (replace with your actual URL)
LOGIC_APP_URL = "https://prod-xx.eastus.logic.azure.com:443/workflows/xxx/triggers/manual/paths/invoke?api-version=2016-10-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=xxx"

def send_notification(user_email, user_name, blood_group, confidence):
    """Send notification via Logic App"""
    try:
        payload = {
            "userId": "1",  # You can get this from request
            "bloodGroup": blood_group,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
            "userEmail": user_email or "user@example.com",
            "userName": user_name or "User"
        }
        
        response = requests.post(LOGIC_APP_URL, json=payload, timeout=30)
        logging.info(f"Logic App response: {response.status_code}")
        
    except Exception as e:
        logging.error(f"Error sending notification: {e}")

# Add this call in your predict function after successful prediction:
# send_notification("user@example.com", "John Doe", predicted_blood_group, confidence)
```

## Step 5: Test the Logic App

1. Use a tool like Postman to send a test request
2. POST to the Logic App URL with sample data:
```json
{
    "userId": "test123",
    "bloodGroup": "A+",
    "confidence": 0.85,
    "timestamp": "2024-01-01T12:00:00Z",
    "userEmail": "test@example.com",
    "userName": "Test User"
}
```

## Advanced Features (Optional)

### 1. SMS Notifications
- Add Twilio connector for SMS alerts
- Useful for critical results

### 2. Database Logging
- Add SQL Database connector
- Store predictions in structured format

### 3. Slack Integration
- Add Slack connector for team notifications
- Useful for monitoring system usage

### 4. Power BI Integration
- Send data to Power BI for analytics
- Create dashboards for prediction trends

## Monitoring

1. Go to Logic App → Overview
2. Check "Runs history" for execution logs
3. Monitor success/failure rates
4. Set up alerts for failures
