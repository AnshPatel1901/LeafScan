"""
Health check endpoint — used by load balancers and k8s probes.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_db
from app.schemas.response import APIResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Liveness probe — is the service up?",
    response_model=APIResponse[dict],
)
async def health_check() -> APIResponse[dict]:
    return APIResponse.ok(
        {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "status": "ok",
        },
        "Service is healthy",
    )


@router.get(
    "/health/db",
    summary="Readiness probe — can the service reach the database?",
    response_model=APIResponse[dict],
)
async def db_health_check(
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        db_status = f"error: {exc}"

    all_ok = db_status == "ok"
    return APIResponse(
        success=all_ok,
        data={"database": db_status},
        message="All systems operational" if all_ok else "Degraded",
    )
