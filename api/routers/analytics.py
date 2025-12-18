"""
Analytics endpoints.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_metrics():
    """Get dashboard metrics."""
    return {"message": "Dashboard metrics endpoint - to be implemented"}


@router.get("/spending")
async def get_spending_by_category():
    """Get spending by category."""
    return {"message": "Spending by category endpoint - to be implemented"}


@router.get("/trends")
async def get_spending_trends():
    """Get spending trends."""
    return {"message": "Spending trends endpoint - to be implemented"}


@router.get("/correlations")
async def get_correlated_payments():
    """Get correlated payments."""
    return {"message": "Correlated payments endpoint - to be implemented"}
