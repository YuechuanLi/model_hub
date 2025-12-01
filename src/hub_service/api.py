from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.db import get_session
from src.common.models import Job, ModelRepo, RepoStatus
from src.hub_service.schemas import ListModelsResponse, RegisterModelRequest

router = APIRouter()


@router.post("/register", response_model=ModelRepo)
async def register_model(
    request: RegisterModelRequest, session: AsyncSession = Depends(get_session)
):
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

    # Trigger sync job
    # TODO: Enqueue sync job via ARQ
    # await enqueue_job(JobType.SYNC, {"repo_id": new_repo.id})

    return new_repo


@router.get("/models", response_model=ListModelsResponse)
async def list_models(
    page: int = 1, page_size: int = 10, session: AsyncSession = Depends(get_session)
):
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


@router.post("/sync")
async def sync_model(repo_id: str, session: AsyncSession = Depends(get_session)):
    # TODO: Implement sync logic
    return {"status": "queued", "job_id": "fake-job-id"}


@router.post("/download")
async def download_model(
    repo_id: str, file_paths: list[str], session: AsyncSession = Depends(get_session)
):
    # TODO: Implement download logic
    return {"status": "queued", "job_id": "fake-job-id"}


@router.get("/jobs")
async def list_jobs(session: AsyncSession = Depends(get_session)):
    statement = select(Job).limit(50)
    results = await session.exec(statement)
    return results.all()
