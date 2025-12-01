"""Job queue utilities for enqueuing background tasks."""

from arq import create_pool
from arq.connections import RedisSettings

from src.common.config import settings
from src.common.models import Job, JobStatus, JobType


async def get_arq_pool():
    """Get ARQ Redis pool for enqueuing jobs."""
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    return await create_pool(redis_settings)


async def enqueue_sync_job(repo_id: str, session) -> Job:
    """Enqueue a metadata sync job.

    Args:
        repo_id: Repository ID to sync
        session: Database session

    Returns:
        Created Job record
    """
    # Create job record
    job = Job(
        type=JobType.SYNC,
        status=JobStatus.PENDING,
        payload={"repo_id": repo_id},
        logs="Job queued",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # Enqueue to ARQ
    pool = await get_arq_pool()
    await pool.enqueue_job("sync_repo_metadata", repo_id=repo_id, job_id=str(job.id))
    await pool.close()

    return job


async def enqueue_download_job(artifact_id: str, session) -> Job:
    """Enqueue an artifact download job.

    Args:
        artifact_id: Artifact ID to download
        session: Database session

    Returns:
        Created Job record
    """
    # Create job record
    job = Job(
        type=JobType.DOWNLOAD,
        status=JobStatus.PENDING,
        payload={"artifact_id": artifact_id},
        logs="Job queued",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # Enqueue to ARQ
    pool = await get_arq_pool()
    await pool.enqueue_job(
        "download_artifact", artifact_id=artifact_id, job_id=str(job.id)
    )
    await pool.close()

    return job


async def enqueue_scan_job(scan_path: str, session) -> Job:
    """Enqueue a local storage scan job.

    Args:
        scan_path: Path to scan
        session: Database session

    Returns:
        Created Job record
    """
    # Create job record
    job = Job(
        type=JobType.SCAN,
        status=JobStatus.PENDING,
        payload={"scan_path": scan_path},
        logs="Job queued",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # Enqueue to ARQ
    pool = await get_arq_pool()
    await pool.enqueue_job(
        "scan_local_storage", scan_path=scan_path, job_id=str(job.id)
    )
    await pool.close()

    return job
