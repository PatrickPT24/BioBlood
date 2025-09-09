import azure.functions as func
import logging
import json
from datetime import datetime

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint"""
    logging.info('Health check requested.')
    
    return func.HttpResponse(
        json.dumps({
            "status": "healthy", 
            "timestamp": datetime.now().isoformat(),
            "message": "BioBlood Function App is running!"
        }),
        status_code=200,
        headers={"Content-Type": "application/json"}
    )

@app.route(route="predict", methods=["POST"])
def predict_simple(req: func.HttpRequest) -> func.HttpResponse:
    """Simple prediction endpoint for testing"""
    logging.info('Prediction requested.')
    
    try:
        # For now, return a mock response
        return func.HttpResponse(
            json.dumps({
                'bloodGroup': 'A+',
                'confidence': 0.85,
                'message': 'Mock prediction - Function App is working!'
            }),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logging.error(f"Prediction error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )
