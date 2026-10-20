from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "books"
    # pymongo waits 30s by default before giving up on an unreachable server.
    mongodb_timeout_ms: int = 5000
    log_level: str = "INFO"
