from uuid import UUID

from pydantic import BaseModel


class RegisterModelRequest(BaseModel):
    vendor: str
    name: str
    source_repo_id: str
    auto_sync: bool = True


class SyncRequest(BaseModel):
    repo_id: str


class DownloadRequest(BaseModel):
    artifact_ids: list[UUID]


class ScanRequest(BaseModel):
    scan_path: str


class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class ListModelsResponse(BaseModel):
    models: list
    total_count: int
