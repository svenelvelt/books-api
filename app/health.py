from fastapi import APIRouter
from pymongo.errors import PyMongoError

from app.db import Database
from app.errors import DatabaseUnavailable
from app.models import HealthStatus

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get("/ready")
async def readiness(db: Database) -> HealthStatus:
    try:
        await db.command("ping")
    except PyMongoError as exc:
        raise DatabaseUnavailable from exc
    return HealthStatus(status="ok")
