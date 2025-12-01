import uuid
from datetime import datetime
from typing import Optional, Any, Dict
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import JSON
from enum import Enum

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
    file_path: str # Relative path in repo
    file_type: ArtifactType = Field(default=ArtifactType.OTHER)
    size_bytes: int = Field(default=0)
    content_hash: Optional[str] = None
    download_status: DownloadStatus = Field(default=DownloadStatus.PENDING)
    local_path: Optional[str] = None
    last_verified_at: Optional[datetime] = None
    
    model_repo: ModelRepo = Relationship(back_populates="artifacts")

class Job(SQLModel, table=True):
    __tablename__ = "job"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    type: JobType
    status: JobStatus = Field(default=JobStatus.PENDING)
    payload: Dict[str, Any] = Field(default={}, sa_type=JSON)
    logs: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
