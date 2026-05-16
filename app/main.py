import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.api import api_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mrp_optimization_engine")

app = FastAPI(
    title="MRP Cutting Optimization Engine",
    version="1.0.0",
    openapi_url=f"/openapi.json"
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy", "engine": "OR-Tools CP-SAT"}