"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.middleware.auth import jwt_auth_middleware
from api.routers import auth, transactions, imports, analytics, health, recurring_payments


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="FinApp API",
        description="Personal finance tracker API with multi-user support",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add JWT authentication middleware
    app.middleware("http")(jwt_auth_middleware)

    # Register routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
    app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["transactions"])
    app.include_router(imports.router, prefix="/api/v1/imports", tags=["imports"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
    app.include_router(recurring_payments.router, prefix="/api/v1/recurring-payments", tags=["recurring-payments"])

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
