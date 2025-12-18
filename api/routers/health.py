"""
Health check endpoints.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import boto3
from botocore.exceptions import ClientError

from api.dependencies import get_db
from api.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check.
    
    Returns a simple status indicating the API is running.
    
    Returns:
        Status message
    """
    return {"status": "healthy", "service": "finapp-api"}


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness check including dependencies.
    
    Checks connectivity to:
    - PostgreSQL database
    - AWS Cognito
    
    Args:
        db: Database session
        
    Returns:
        Status of all dependencies
    """
    checks = {
        "status": "ready",
        "database": "unknown",
        "cognito": "unknown"
    }
    
    # Check database connectivity
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        checks["database"] = "connected"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
        checks["status"] = "not_ready"
    
    # Check Cognito connectivity
    try:
        cognito_client = boto3.client(
            'cognito-idp',
            region_name=settings.COGNITO_REGION
        )
        # Try to describe the user pool to verify connectivity
        cognito_client.describe_user_pool(
            UserPoolId=settings.COGNITO_USER_POOL_ID
        )
        checks["cognito"] = "connected"
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            checks["cognito"] = "error: user pool not found"
        else:
            checks["cognito"] = f"error: {error_code}"
        checks["status"] = "not_ready"
    except Exception as e:
        checks["cognito"] = f"error: {str(e)}"
        checks["status"] = "not_ready"
    
    # Return appropriate status code
    if checks["status"] == "not_ready":
        return checks, status.HTTP_503_SERVICE_UNAVAILABLE
    
    return checks
