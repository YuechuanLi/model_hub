import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON
from sqlmodel import Field, Relationship, SQLModel


class RepoStatus(str, Enum):
    REGISTERED = "registered"
    SYNCED = "synced"
    ERROR = "error"


class ArtifactType(str, Enum):
    MODEL = "model"
    CONFIG = "config"
    TOKENIZER = "tokenizer"
    OTHER = "other"


class DownloadStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, Enum):
    SYNC = "sync"
    DOWNLOAD = "download"
    SCAN = "scan"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ModelRepo(SQLModel, table=True):
    __tablename__ = "model_repo"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    vendor: str
    name: str
    source: str = Field(default="huggingface")
    repo_id: str = Field(index=True, unique=True)
    status: RepoStatus = Field(default=RepoStatus.REGISTERED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    artifacts: list["ModelArtifact"] = Relationship(back_populates="model_repo")


class ModelArtifact(SQLModel, table=True):
    __tablename__ = "model_artifact"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    model_repo_id: uuid.UUID = Field(foreign_key="model_repo.id")
    file_path: str  # Relative path in repo
    file_type: ArtifactType = Field(default=ArtifactType.OTHER)
    size_bytes: int = Field(default=0)
    content_hash: str | None = None
    download_status: DownloadStatus = Field(default=DownloadStatus.PENDING)
    local_path: str | None = None
    last_verified_at: datetime | None = None

    model_repo: ModelRepo = Relationship(back_populates="artifacts")


class Job(SQLModel, table=True):
    __tablename__ = "job"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    type: JobType
    status: JobStatus = Field(default=JobStatus.PENDING)
    payload: dict[str, Any] = Field(default={}, sa_type=JSON)
    logs: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
