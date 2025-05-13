from app.core.config import get_settings
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
async def health():
    settings = get_settings()
    return {
        "status": "ok",
        "env": {
            "db": settings.database_url,
            "bucket": settings.s3_bucket,
        },
    }
