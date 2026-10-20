from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pymongo import AsyncMongoClient

from app import authors, books, health, publishers
from app.config import Settings
from app.db import create_indexes
from app.errors import register_error_handlers
from app.logs import configure_logging, log_requests


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        client = AsyncMongoClient(
            settings.mongodb_uri,
            tz_aware=True,
            serverSelectionTimeoutMS=settings.mongodb_timeout_ms,
        )
        app.state.db = client[settings.mongodb_database]
        await create_indexes(app.state.db)
        try:
            yield
        finally:
            await client.close()

    app = FastAPI(title="Books API", lifespan=lifespan)
    register_error_handlers(app)
    app.middleware("http")(log_requests)
    app.include_router(health.router)
    app.include_router(books.router)
    app.include_router(authors.router)
    app.include_router(publishers.router)
    return app


app = create_app()
