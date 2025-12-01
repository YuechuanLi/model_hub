from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.common.db import engine
from src.hub_service.api import router as hub_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables (for now, usually use Alembic)
    async with engine.begin():
        # await conn.run_sync(SQLModel.metadata.create_all)
        pass
    yield
    # Shutdown


app = FastAPI(title="Model Hub API", version="0.1.0", lifespan=lifespan)

app.include_router(hub_router, prefix="/v1/hub", tags=["hub"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
