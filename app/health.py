from fastapi import APIRouter

from app.db import Database

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def readiness(db: Database) -> dict[str, str]:
    await db.command("ping")
    return {"status": "ok"}
