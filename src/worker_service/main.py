from arq.connections import RedisSettings

from src.common.config import settings
from src.worker_service.tasks import (
    download_artifact,
    scan_local_storage,
    sync_repo_metadata,
)


async def startup(ctx):
    print("Worker starting up...")


async def shutdown(ctx):
    print("Worker shutting down...")


class WorkerSettings:
    functions = [sync_repo_metadata, download_artifact, scan_local_storage]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    on_startup = startup
    on_shutdown = shutdown
