from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "books"
    # pymongo waits 30s by default; fail faster so health checks and requests
    # get an answer within a load balancer's timeout.
    mongodb_timeout_ms: int = 5000
