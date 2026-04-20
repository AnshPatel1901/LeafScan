"""
Central router — mounts all sub-routers onto the FastAPI application.
"""

from fastapi import APIRouter

from app.api import auth, health, history, predict, tts

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(predict.router)
api_router.include_router(history.router)
api_router.include_router(tts.router, prefix="/tts")
