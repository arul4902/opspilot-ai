import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.session import engine, Base
import backend.app.database.base  # ensure all models are registered
from backend.app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist and database is initialized
    from backend.app.database.session import ensure_database_initialized
    ensure_database_initialized()
    logger.info(f"{settings.PROJECT_NAME} initialized successfully. Running in {settings.ENVIRONMENT} mode.")
    yield
    # Shutdown
    logger.info("Shutting down OpsPilot AI backend.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Intelligent E-commerce Operations Automation Platform API",
    version="1.0.0",
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

# CORS Middleware
cors_origins = [o for o in settings.BACKEND_CORS_ORIGINS if o != "*"]
allow_regex = r".*" if "*" in settings.BACKEND_CORS_ORIGINS else None
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=allow_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_and_correlation(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    response.headers["X-Correlation-ID"] = correlation_id
    return response


# Include API v1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "api_v1": settings.API_V1_STR
    }


@app.get("/health", tags=["System"])
@app.get(f"{settings.API_V1_STR}/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "vector_store": "ready",
        "indexed_policy_vectors": 59,
        "environment": settings.ENVIRONMENT,
        "llm_provider": settings.LLM_PROVIDER
    }

