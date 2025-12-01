"""Worker tasks for Model Hub operations."""

import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.config import settings
from src.common.db import async_engine
from src.common.hf_client import HFClient
from src.common.models import (
    ArtifactType,
    DownloadStatus,
    Job,
    JobStatus,
    ModelArtifact,
    ModelRepo,
    RepoStatus,
)


async def sync_repo_metadata(ctx: dict, repo_id: str, job_id: str | None = None):
    """Sync repository metadata from HuggingFace.

    This task:
    1. Fetches file list from HuggingFace
    2. Creates ModelArtifact records for each file
    3. Downloads small metadata files (config.json, etc.)
    4. Updates ModelRepo status

    Args:
        ctx: ARQ context
        repo_id: Repository ID (e.g., "Wan-AI/Wan2.1-T2V-1.3B")
        job_id: Optional job ID for tracking
    """
    async with AsyncSession(async_engine) as session:
        try:
            # Update job status to running
            if job_id:
                job = await session.get(Job, uuid.UUID(job_id))
                if job:
                    job.status = JobStatus.RUNNING
                    job.logs = f"Starting metadata sync for {repo_id}"
                    await session.commit()

            # Get ModelRepo record
            statement = select(ModelRepo).where(ModelRepo.repo_id == repo_id)
            result = await session.exec(statement)
            model_repo = result.first()

            if not model_repo:
                raise ValueError(f"ModelRepo not found: {repo_id}")

            # Initialize HF client
            hf_client = HFClient()

            # Fetch file list from HuggingFace
            files = await hf_client.list_repo_files(repo_id)

            # Process each file
            artifacts_created = 0
            metadata_files_downloaded = 0

            for file_info in files:
                file_path = file_info["path"]
                file_size = file_info["size"]

                # Check if artifact already exists
                artifact_statement = select(ModelArtifact).where(
                    ModelArtifact.model_repo_id == model_repo.id,
                    ModelArtifact.file_path == file_path,
                )
                artifact_result = await session.exec(artifact_statement)
                existing_artifact = artifact_result.first()

                if existing_artifact:
                    # Update existing artifact
                    existing_artifact.size_bytes = file_size
                    existing_artifact.content_hash = file_info.get("blob_id")
                else:
                    # Classify file type
                    file_type_str = hf_client.classify_file_type(file_path)
                    file_type = ArtifactType(file_type_str)

                    # Infer format and precision
                    file_format, precision = hf_client.infer_format_and_precision(
                        file_path
                    )

                    # Create new artifact
                    artifact = ModelArtifact(
                        model_repo_id=model_repo.id,
                        file_path=file_path,
                        file_type=file_type,
                        size_bytes=file_size,
                        content_hash=file_info.get("blob_id"),
                        download_status=DownloadStatus.PENDING,
                    )
                    session.add(artifact)
                    artifacts_created += 1

                # Download small metadata files immediately
                if file_type_str in ["config", "tokenizer"] and file_size < 10_000_000:
                    # 10MB threshold
                    try:
                        local_dir = (
                            Path(settings.MODEL_STORE_PATH)
                            / "metadata"
                            / repo_id.replace("/", "_")
                        )
                        downloaded_path = await hf_client.download_file(
                            repo_id=repo_id,
                            file_path=file_path,
                            local_dir=local_dir,
                        )

                        # Update artifact with local path
                        if existing_artifact:
                            existing_artifact.local_path = str(downloaded_path)
                            existing_artifact.download_status = DownloadStatus.COMPLETED
                            existing_artifact.last_verified_at = datetime.utcnow()
                        else:
                            artifact.local_path = str(downloaded_path)
                            artifact.download_status = DownloadStatus.COMPLETED
                            artifact.last_verified_at = datetime.utcnow()

                        metadata_files_downloaded += 1
                    except Exception as e:
                        print(f"Failed to download metadata file {file_path}: {e}")

            # Update ModelRepo status
            model_repo.status = RepoStatus.SYNCED
            model_repo.updated_at = datetime.utcnow()

            await session.commit()

            # Update job status to completed
            if job_id:
                job = await session.get(Job, uuid.UUID(job_id))
                if job:
                    job.status = JobStatus.COMPLETED
                    job.logs = (
                        f"Synced {len(files)} files, "
                        f"created {artifacts_created} new artifacts, "
                        f"downloaded {metadata_files_downloaded} metadata files"
                    )
                    await session.commit()

            return {
                "status": "success",
                "files_synced": len(files),
                "artifacts_created": artifacts_created,
                "metadata_downloaded": metadata_files_downloaded,
            }

        except Exception as e:
            # Update job status to failed
            if job_id:
                job = await session.get(Job, uuid.UUID(job_id))
                if job:
                    job.status = JobStatus.FAILED
                    job.logs = f"Error: {str(e)}"
                    await session.commit()

            raise


async def download_artifact(
    ctx: dict, artifact_id: str, job_id: str | None = None
) -> dict:
    """Download a model artifact from HuggingFace.

    This task:
    1. Downloads the file from HuggingFace
    2. Computes SHA256 hash
    3. Stores in content-addressable storage
    4. Updates ModelArtifact record

    Args:
        ctx: ARQ context
        artifact_id: UUID of the artifact to download
        job_id: Optional job ID for tracking

    Returns:
        Dictionary with download status and metadata
    """
    async with AsyncSession(async_engine) as session:
        try:
            # Update job status
            if job_id:
                job = await session.get(Job, uuid.UUID(job_id))
                if job:
                    job.status = JobStatus.RUNNING
                    job.logs = f"Starting download for artifact {artifact_id}"
                    await session.commit()

            # Get artifact
            artifact = await session.get(ModelArtifact, uuid.UUID(artifact_id))
            if not artifact:
                raise ValueError(f"Artifact not found: {artifact_id}")

            # Get model repo
            model_repo = await session.get(ModelRepo, artifact.model_repo_id)
            if not model_repo:
                raise ValueError(f"ModelRepo not found: {artifact.model_repo_id}")

            # Update artifact status
            artifact.download_status = DownloadStatus.DOWNLOADING
            await session.commit()

            # Initialize HF client
            hf_client = HFClient()

            # Download to temporary location first
            temp_dir = Path(settings.MODEL_STORE_PATH) / "temp"
            downloaded_path = await hf_client.download_file(
                repo_id=model_repo.repo_id,
                file_path=artifact.file_path,
                local_dir=temp_dir,
            )

            # Compute hash
            file_hash = await hf_client.compute_file_hash(downloaded_path)

            # Move to content-addressable storage
            blob_dir = Path(settings.MODEL_STORE_PATH) / "blobs" / "sha256"
            blob_dir.mkdir(parents=True, exist_ok=True)
            final_path = blob_dir / file_hash

            # Check if file already exists (deduplication)
            if final_path.exists():
                # File already exists, just update reference
                downloaded_path.unlink()
            else:
                # Move file to final location
                downloaded_path.rename(final_path)

            # Update artifact record
            artifact.local_path = str(final_path)
            artifact.content_hash = file_hash
            artifact.download_status = DownloadStatus.COMPLETED
            artifact.last_verified_at = datetime.utcnow()

            await session.commit()

            # Update job status
            if job_id:
                job = await session.get(Job, uuid.UUID(job_id))
                if job:
                    job.status = JobStatus.COMPLETED
                    job.logs = f"Downloaded artifact to {final_path}"
                    await session.commit()

            return {
                "status": "success",
                "artifact_id": artifact_id,
                "local_path": str(final_path),
                "hash": file_hash,
            }

        except Exception as e:
            # Update artifact status
            try:
                artifact = await session.get(ModelArtifact, uuid.UUID(artifact_id))
                if artifact:
                    artifact.download_status = DownloadStatus.FAILED
                    await session.commit()
            except Exception:
                pass

            # Update job status
            if job_id:
                try:
                    job = await session.get(Job, uuid.UUID(job_id))
                    if job:
                        job.status = JobStatus.FAILED
                        job.logs = f"Error: {str(e)}"
                        await session.commit()
                except Exception:
                    pass

            raise


async def scan_local_storage(ctx: dict, scan_path: str, job_id: str | None = None):
    """Scan local storage for existing model files and register them.

    This task:
    1. Walks the directory structure
    2. Identifies model repositories (by config.json or model_index.json)
    3. Computes hashes for found files
    4. Creates ModelRepo and ModelArtifact records

    Args:
        ctx: ARQ context
        scan_path: Path to scan
        job_id: Optional job ID for tracking
    """
    async with AsyncSession(async_engine) as session:
        try:
            if job_id:
                job = await session.get(Job, uuid.UUID(job_id))
                if job:
                    job.status = JobStatus.RUNNING
                    job.logs = f"Starting scan of {scan_path}"
                    await session.commit()

            # TODO: Implement local storage scanning logic
            # This is a complex task that requires:
            # 1. Walking directory structure
            # 2. Identifying model repos by config files
            # 3. Computing hashes
            # 4. Creating/updating database records

            if job_id:
                job = await session.get(Job, uuid.UUID(job_id))
                if job:
                    job.status = JobStatus.COMPLETED
                    job.logs = "Scan completed (not yet implemented)"
                    await session.commit()

            return {"status": "pending_implementation"}

        except Exception as e:
            if job_id:
                job = await session.get(Job, uuid.UUID(job_id))
                if job:
                    job.status = JobStatus.FAILED
                    job.logs = f"Error: {str(e)}"
                    await session.commit()
            raise
