from fastapi import APIRouter
from app.api.v1.endpoints import optimization, inference

api_router = APIRouter()
api_router.include_router(optimization.router, tags=["Dynamic"])
api_router.include_router(inference.router, tags=["Inference"])
