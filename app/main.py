from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pymongo import AsyncMongoClient

from app import health
from app.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        client = AsyncMongoClient(settings.mongodb_uri, tz_aware=True)
        app.state.db = client[settings.mongodb_database]
        try:
            yield
        finally:
            await client.close()

    app = FastAPI(title="Books API", lifespan=lifespan)
    app.include_router(health.router)
    return app


app = create_app()
