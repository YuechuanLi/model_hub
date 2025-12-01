from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.db import get_session
from src.common.job_queue import (
    enqueue_download_job,
    enqueue_scan_job,
    enqueue_sync_job,
)
from src.common.models import Job, ModelArtifact, ModelRepo, RepoStatus
from src.hub_service.schemas import (
    DownloadRequest,
    JobResponse,
    ListModelsResponse,
    RegisterModelRequest,
    ScanRequest,
    SyncRequest,
)

router = APIRouter()


@router.post("/register", response_model=ModelRepo)
async def register_model(
    request: RegisterModelRequest, session: AsyncSession = Depends(get_session)
):
    """Register a new model repository.

    This creates a ModelRepo record and optionally triggers a metadata sync job.
    """
    # Check if already exists
    statement = select(ModelRepo).where(ModelRepo.repo_id == request.source_repo_id)
    results = await session.exec(statement)
    existing_repo = results.first()

    if existing_repo:
        raise HTTPException(status_code=400, detail="Model already registered")

    new_repo = ModelRepo(
        vendor=request.vendor,
        name=request.name,
        repo_id=request.source_repo_id,
        status=RepoStatus.REGISTERED,
    )
    session.add(new_repo)
    await session.commit()
    await session.refresh(new_repo)

    # Trigger sync job if requested
    if request.auto_sync:
        await enqueue_sync_job(new_repo.repo_id, session)

    return new_repo


@router.get("/models", response_model=ListModelsResponse)
async def list_models(
    page: int = 1, page_size: int = 10, session: AsyncSession = Depends(get_session)
):
    """List all registered models with pagination."""
    offset = (page - 1) * page_size
    statement = select(ModelRepo).offset(offset).limit(page_size)
    results = await session.exec(statement)
    models = results.all()

    # Count total (simplified)
    # TODO: Optimize count query
    count_statement = select(ModelRepo)
    all_results = await session.exec(count_statement)
    total_count = len(all_results.all())

    return ListModelsResponse(models=models, total_count=total_count)


@router.post("/sync", response_model=JobResponse)
async def sync_model(
    request: SyncRequest, session: AsyncSession = Depends(get_session)
):
    """Trigger metadata sync for a repository.

    This fetches the file list from HuggingFace and creates ModelArtifact records.
    Small metadata files (config.json, etc.) are downloaded immediately.
    """
    # Verify repo exists
    statement = select(ModelRepo).where(ModelRepo.repo_id == request.repo_id)
    results = await session.exec(statement)
    repo = results.first()

    if not repo:
        raise HTTPException(status_code=404, detail="Model repository not found")

    # Enqueue sync job
    job = await enqueue_sync_job(request.repo_id, session)

    return JobResponse(job_id=str(job.id), status=job.status, message="Sync job queued")


@router.post("/download", response_model=JobResponse)
async def download_artifacts(
    request: DownloadRequest, session: AsyncSession = Depends(get_session)
):
    """Trigger download for specific artifacts.

    Downloads model files and stores them in content-addressable storage.
    """
    # Verify artifacts exist
    jobs = []
    for artifact_id in request.artifact_ids:
        artifact = await session.get(ModelArtifact, artifact_id)
        if not artifact:
            raise HTTPException(
                status_code=404, detail=f"Artifact not found: {artifact_id}"
            )

        # Enqueue download job
        job = await enqueue_download_job(str(artifact_id), session)
        jobs.append(job)

    return JobResponse(
        job_id=str(jobs[0].id) if jobs else "",
        status=jobs[0].status if jobs else "pending",
        message=f"Queued {len(jobs)} download job(s)",
    )


@router.post("/scan", response_model=JobResponse)
async def scan_storage(
    request: ScanRequest, session: AsyncSession = Depends(get_session)
):
    """Trigger a scan of local storage to import existing models."""
    job = await enqueue_scan_job(request.scan_path, session)

    return JobResponse(job_id=str(job.id), status=job.status, message="Scan job queued")


@router.get("/jobs")
async def list_jobs(session: AsyncSession = Depends(get_session)):
    """List recent jobs."""
    statement = select(Job).limit(50).order_by(Job.created_at.desc())
    results = await session.exec(statement)
    return results.all()


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)):
    """Get job details by ID."""
    import uuid

    try:
        job = await session.get(Job, uuid.UUID(job_id))
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format") from None
