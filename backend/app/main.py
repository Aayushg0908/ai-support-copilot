"""
FastAPI application entry point.

This is the main file that starts the entire application.
It wires together all routers, middleware, and startup events.

Run with: uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppException
from app.db.init_db import init_database

# Import all API routers
from app.api.v1.auth import router as auth_router
from app.api.v1.organizations import router as org_router
from app.api.v1.users import router as users_router
from app.api.v1.tickets import router as tickets_router
from app.api.v1.comments import router as comments_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.ai import router as ai_router
from app.api.v1.audit import router as audit_router


# ──────────────────────────────────────────────
# Application Lifecycle
# ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events.
    
    Startup:
    - Initialize database (create tables, enable extensions)
    - Seed demo data if in development mode
    
    Shutdown:
    - Clean up resources (database connections closed automatically)
    """
    # STARTUP: Runs when server starts
    print(f"\n{'='*50}")
    print(f"  {settings.APP_NAME}")
    print(f"  Environment: {settings.APP_ENV}")
    print(f"  Server: http://{settings.HOST}:{settings.PORT}")
    print(f"  API Docs: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"{'='*50}\n")
    
    init_database()
    
    yield  # Application runs here
    
    # SHUTDOWN: Runs when server stops
    print("\nShutting down...")


# ──────────────────────────────────────────────
# Create FastAPI Application
# ──────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered customer support platform",
    version="1.0.0",
    docs_url="/docs",          # Swagger UI
    redoc_url="/redoc",        # ReDoc UI
    lifespan=lifespan,
)


# ──────────────────────────────────────────────
# CORS Middleware
# ──────────────────────────────────────────────
# Allows the React frontend to call the API.
# In production, restrict origins to your actual domain.

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],       # GET, POST, PUT, DELETE, PATCH, OPTIONS
    allow_headers=["*"],       # Authorization, Content-Type, etc.
)


# ──────────────────────────────────────────────
# Global Exception Handler
# ──────────────────────────────────────────────

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """
    Catch all our custom exceptions and return consistent format.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Catch any unexpected errors and return a generic 500 response.
    Prevents leaking internal error details to clients.
    """
    # Log the actual error for debugging
    print(f"Unhandled error: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again later."
            }
        },
    )


# ──────────────────────────────────────────────
# Health Check
# ──────────────────────────────────────────────

@app.get("/health", tags=["Health"])
def health_check():
    """
    Simple health check endpoint.
    Used by monitoring tools and load balancers
    to verify the application is running.
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }

# ──────────────────────────────────────────────
# Register API Routers
# ──────────────────────────────────────────────
# All routes are prefixed with /api/v1 for versioning

app.include_router(auth_router, prefix="/api/v1")
app.include_router(org_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(tickets_router, prefix="/api/v1")
app.include_router(comments_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")


# ──────────────────────────────────────────────
# Root Endpoint
# ──────────────────────────────────────────────

@app.get("/", tags=["Root"])
def root():
    """
    Welcome endpoint - confirms the API is running.
    """
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }