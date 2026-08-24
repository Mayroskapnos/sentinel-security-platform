from fastapi import APIRouter

from app.api.v1.routes.assets import router as assets_router
from app.api.v1.routes.dashboard import router as dashboard_router
from app.api.v1.routes.events import router as events_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.telemetry import router as telemetry_router
from app.api.v1.routes.websockets import router as websockets_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(assets_router)
api_router.include_router(events_router)
api_router.include_router(dashboard_router)
api_router.include_router(telemetry_router)
api_router.include_router(websockets_router)
