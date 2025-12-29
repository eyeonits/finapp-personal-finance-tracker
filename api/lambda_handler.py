"""
AWS Lambda handler for FastAPI application.
Uses Mangum to adapt ASGI to Lambda/API Gateway events.
"""
from mangum import Mangum
from api.main import app

# Create Mangum handler
# lifespan="off" is recommended for Lambda to avoid startup/shutdown issues
handler = Mangum(app, lifespan="off")

