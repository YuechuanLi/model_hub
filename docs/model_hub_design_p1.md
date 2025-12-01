# Model Hub Design - Phase 1: Local Foundation

## 1. Problem & Goals

### 1.1 Problem
We need a robust, local-first Model Hub to manage machine learning models (LLMs, Vision, Video, etc.) for development. It must serve as a centralized registry and storage for model artifacts, decoupling application logic from external model sources like HuggingFace.

### 1.2 Goals
*   **Local-First & Cloud-Ready**: Build for local development (Linux + GPU) but ensure architecture allows seamless migration to cloud (Kubernetes + S3) later.
*   **Centralized Storage**: Store models and metadata locally to avoid redundant downloads and ensure offline availability.
*   **HuggingFace Sync**: exclusively use HuggingFace as the source of truth for model repositories.
*   **Core Hub Functions**: Implement robust Registration, Synchronization (metadata), and Download (artifacts) capabilities.
*   **Admin Interface**: Provide a web UI for developers to inspect registered models, monitor sync/download jobs, and explore available artifacts.
*   **Testability**: Enable API testing without waiting for massive model downloads by implementing a mock server/client strategy.

### 1.3 Non-Goals (Phase 1)
*   Multi-tenant authentication or quotas.
*   Complex multi-GPU scheduling.
*   Serving inference traffic (this is the *Hub*, not the *Serving* layer, though they may coexist).
*   Sources other than HuggingFace (e.g., Civitai, Kaggle).

---

## 2. Context & Constraints

### 2.1 Context
*   **User**: Single developer or small team working locally.
*   **Hardware**: Linux workstation with NVIDIA GPU (e.g., RTX 4090).
*   **Stack**: Python (FastAPI), PostgreSQL, React/Next.js (Admin UI), Docker.

### 2.2 Constraints
*   **Storage**: Local filesystem (e.g., `/data/model-store`).
*   **Network**: Dependent on HuggingFace availability for initial sync.
*   **Compatibility**: Must handle various model formats (safetensors, gguf, bin, onnx).

---

## 3. High-Level Architecture

### 3.1 System Components

1.  **Hub API Service (FastAPI)**
    *   **Role**: The brain of the system. Manages metadata, dispatches jobs, and serves the Admin UI API.
    *   **Endpoints**:
        *   `POST /v1/hub/register`: Register a new HF repo.
        *   `POST /v1/hub/sync`: Trigger metadata sync.
        *   `POST /v1/hub/download`: Trigger artifact download.
        *   `POST /v1/hub/scan`: Trigger a scan of local storage to import existing models.
        *   `GET /v1/hub/models`: List models and status.
        *   `GET /v1/hub/jobs`: Check background job status.

2.  **Worker Service (Python/RQ or Celery)**
    *   **Role**: Executes long-running tasks asynchronously.
    *   **Tasks**:
        *   `sync_repo_metadata`: Fetches file lists and metadata from HF.
        *   `download_artifact`: Downloads large files with resume capability and checksum verification.
        *   `scan_local_storage`: Walks local directories to identify and register existing model repos and artifacts.

3.  **Metadata Store (PostgreSQL)**
    *   **Role**: Relational source of truth for Repos, Files, Artifacts, and Jobs.

4.  **Model Artifact Store (Local Filesystem)**
    *   **Role**: Physical storage for model files.
    *   **Structure**: Content-addressable storage (CAS) preferred for deduplication, or structured repo paths.
    *   **Path**: default to `file:///data/model-store/`

5.  **Admin Dashboard (Web UI)**
    *   **Role**: Visual interface for the Hub.
    *   **Tech**: React / Next.js / Vite.

6.  **Mock HF Server (Testing)**
    *   **Role**: Simulates HuggingFace API responses and file downloads for fast integration testing.

### 3.2 Data Flow
1.  **User** registers `Wan-AI/Wan2.1-T2V-1.3B` via Admin UI.
2.  **API** creates `ModelRepo` record and enqueues `sync_metadata` job.
3.  **Worker** fetches file list from HF, populates `Artifact` records in Postgres.
4.  **User** clicks "Download" for specific files or the whole model.
5.  **API** enqueues `download_artifact` jobs.
6.  **Worker** streams bytes to **Model Artifact Store**, updates `Artifact` status in DB.

7.  **Local Import Flow**
    *   **User** triggers scan on `/data/model-store` (or specific subpath).
    *   **Worker** walks directory structure expecting `vendor/model_name` layout.
    *   **Worker** identifies `config.json` or `model_index.json` to infer Model ID.
    *   **Worker** computes SHA256 of found files.
    *   **Worker** registers `ModelRepo` (if new), creates `Artifact` entries for the local files.
    *   **Result**: Models already on disk become immediately available in the Hub without re-downloading.

---

## 4. Data Model (Phase 1)

### 4.1 `model_repo`
*   `id`: UUID
*   `vendor`: `Wan-AI`
*   `name`: `Wan2.1-T2V-1.3B`
*   `source`: `huggingface`
*   `repo_id`: `Wan-AI/Wan2.1-T2V-1.3B`
*   `status`: `registered`, `synced`, `error`

### 4.2 `model_artifact`
*   `id`: UUID
*   `model_repo_id`: FK to `model_repo`
*   `file_path`: `unet/diffusion_pytorch_model.safetensors` (Relative path in repo)
*   `file_type`: `model`, `config`, `tokenizer`
*   `size_bytes`: BigInt
*   `content_hash`: SHA256 (from HF metadata or computed)
*   `download_status`: `pending`, `downloading`, `completed`, `failed`
*   `local_path`: `/data/model-store/blobs/sha256/...` (Nullable, set when downloaded)
*   `last_verified_at`: Timestamp

### 4.4 `job`
*   `id`: UUID
*   `type`: `sync`, `download`
*   `status`: `pending`, `running`, `completed`, `failed`
*   `payload`: JSON (repo_id, file_paths, etc.)
*   `logs`: Text/JSON

---

## 5. Admin Website Design

### 5.1 Dashboard
*   **Overview Cards**: Total Models, Total Storage Used, Active Jobs, Failed Jobs.
*   **Recent Activity**: List of recent sync/download events.

### 5.2 Model Explorer
*   **List View**: Table of registered models with status indicators (Synced, Downloaded).
*   **Detail View**:
    *   Header: Model Name, Vendor, Link to HF.
    *   **File Browser**: Tree view of files in the repo.
        *   Columns: Name, Size, Type, Status (Remote/Local).
        *   Actions: "Download" button per file or folder.
    *   **Metadata**: View parsed `config.json` or `model_index.json` if available.

### 5.3 Job Monitor
*   **Live Feed**: Real-time updates of running jobs.
*   **History**: Searchable history of past jobs.
*   **Details**: View logs/traceback for failed jobs.

### 5.4 Settings
*   **Storage Path**: Configure where models are stored.
*   **HF Token**: Manage HuggingFace API token.

---

## 6. Testing Strategy

### 6.1 The Problem
Downloading 50GB models during CI/CD or local dev iteration is impractical.

### 6.2 The Solution: Mock HF Server
We will build a lightweight HTTP server (using FastAPI or Go) that mimics the HuggingFace Hub API.

*   **Mock Endpoints**:
    *   `GET /api/models/{repo_id}`: Returns JSON metadata.
    *   `GET /api/models/{repo_id}/tree/{revision}`: Returns file listing.
    *   `GET /{repo_id}/resolve/{revision}/{filename}`: Returns dummy binary content (e.g., 1KB of zeros or random bytes) with correct Content-Length headers to test download logic without bandwidth.

### 6.3 Test Client
A Python client library that interacts with our Hub API, configured to point to the Mock HF Server during tests.

*   **Scenario 1: Registration**: Register a mock repo, assert DB state.
*   **Scenario 2: Sync**: Trigger sync, assert `Artifact` records match mock data.
*   **Scenario 3: Download**: Trigger download, assert file exists locally and `Artifact` record is created. Verify checksum logic (mock server provides known checksum).

---

## 7. Implementation Plan

### Phase 1.1: Foundation
1.  **Setup Project**: Initialize repo, Docker Compose (Postgres, Redis).
2.  **DB Schema**: Implement Alembic migrations for Core Entities.
3.  **API Skeleton**: Basic FastAPI app with DB connection.

### Phase 1.2: Core Logic
1.  **HF Client**: Wrapper around `huggingface_hub` library or direct HTTP calls.
2.  **Sync Logic**: Implement `sync_metadata` job.
3.  **Download Logic**: Implement `download_artifact` job with chunked downloading and SHA256 verification.

### Phase 1.3: Admin UI
1.  **Frontend Setup**: Vite + React + Tailwind.
2.  **Model List & Detail**: Components to display repo structure.
3.  **Job Status**: Polling or WebSocket for job updates.

### Phase 1.4: Testing Infrastructure
1.  **Mock Server**: Build the Mock HF Server.
2.  **Integration Tests**: Write pytest suite using the Mock Server.

---

## 8. Future Compatibility (Cloud)
*   **Storage**: The `Artifact Store` abstraction allows swapping the local filesystem backend for an S3-compatible backend (MinIO/AWS S3) without changing core logic.
*   **Workers**: The job queue system (Redis + Worker) scales horizontally in Kubernetes.
*   **Database**: Postgres is standard for cloud deployments.

---

## 9. Tech Stack & Tools

### 9.1 Core Stack
*   **Language**: Python 3.12+ (Leveraging latest async features and typing).
*   **Web Framework**: **FastAPI** (High performance, easy OpenAPI integration).
*   **Model Serving**: **BentoML** (Standardized model packaging and serving).
*   **Database**: **PostgreSQL** (16+).
*   **ORM**: **SQLModel** (Combines SQLAlchemy and Pydantic; ideal for FastAPI).
*   **Migrations**: **Alembic**.
*   **Async Task Queue**: **ARQ** (Redis-based).
    *   *Why ARQ?* Lightweight, native `asyncio` support, faster than Celery for our use case, and integrates seamlessly with FastAPI.
*   **Package Manager**: **uv**.
    *   *Why uv?* Extremely fast, manages Python versions (ensures 3.12), and handles dependencies efficiently.

### 9.2 Frontend (Admin Website)
*   **Framework**: **React** (v18+) with **TypeScript**.
*   **Build Tool**: **Vite** (Fast HMR).
*   **Styling**: **Tailwind CSS** (Utility-first) + **Shadcn/ui** (Accessible, premium components).
*   **State Management**: **TanStack Query** (React Query) for server state/caching.
*   **Routing**: **TanStack Router** or **React Router**.

### 9.3 Protocol Buffers & gRPC
*   **Schema Generator**: **Buf**.
    *   *Why Buf?* Modern standard for Protobuf management. Handles linting, breaking change detection, and generation better than raw `protoc`.
*   **Python Generation**: **betterproto** (v2.0+).
    *   *Why betterproto?* Generates clean, idiomatic, and fully typed Python dataclasses (async-native) instead of the verbose default `protoc` output. Perfect for modern Python 3.12+ async codebases.

### 9.4 Observability
*   **Platform**: **SigNoz**.
*   **Instrumentation**: **OpenTelemetry** (Python auto-instrumentation).

### 9.5 Linting & Code Quality
*   **Linter & Formatter**: **Ruff**.
    *   *Rules*:
        *   `E`, `W` (pycodestyle)
        *   `F` (Pyflakes)
        *   `I` (isort)
        *   `B` (flake8-bugbear)
        *   `UP` (pyupgrade)
        *   `N` (pep8-naming)
    *   *Config* (`pyproject.toml`):
        ```toml
        [tool.ruff]
        line-length = 88
        target-version = "py312"

        [tool.ruff.lint]
        select = ["E", "F", "I", "B", "UP", "N"]
        ignore = ["E501"] # Line too long (handled by formatter)
        ```
*   **Type Checking**: **Mypy**.
    *   *Config* (`pyproject.toml`):
        ```toml
        [tool.mypy]
        python_version = "3.12"
        strict = true
        ignore_missing_imports = true
        disallow_untyped_defs = true
        ```
*   **Pre-commit**: Hooks for `ruff` and `mypy`.

### 9.6 AI/ML
*   **Framework**: **PyTorch** (>=2.4).
*   **Acceleration**: CUDA 12.x (matching system drivers).

---

## 10. API Design & Protocols

### 10.1 Schema Management (Protobuf & Buf)
We will use **Protocol Buffers (Protobuf)** as the single source of truth for our data models and API interfaces.

*   **Tooling**: **Buf** (https://buf.build).
    *   **Why Buf?**: It replaces the complex `protoc` workflow with a simple `buf.yaml`. It provides built-in linting (`buf lint`), breaking change detection (`buf breaking`), and consistent code generation.
*   **Workflow**:
    1.  Define API/Models in `proto/v1/*.proto`.
    2.  Use `buf generate` with the `betterproto` plugin to create clean Python dataclasses and async gRPC stubs.
    3.  FastAPI uses these generated definitions for request/response validation (where applicable) or internal mapping.

### 10.2 Public API (REST/HTTP)
**Purpose**: Served to the Admin Website, CLI tools, and external integrations.
**Implementation**: FastAPI.

*   **Style**: RESTful resources.
*   **Content-Type**: `application/json`.
*   **Example Definitions**:

```protobuf
// proto/v1/hub_service.proto
service HubService {
  // Register a new model repository
  rpc RegisterModel(RegisterModelRequest) returns (ModelRepo);
  
  // List available models
  rpc ListModels(ListModelsRequest) returns (ListModelsResponse);
}

message RegisterModelRequest {
  string vendor = 1;
  string name = 2;
  string source_repo_id = 3; // e.g. "Wan-AI/Wan2.1-T2V-1.3B"
}
```

*   **Mapped REST Endpoints**:
    *   `POST /v1/models` -> Calls `RegisterModel` logic.
    *   `GET /v1/models` -> Calls `ListModels` logic.

### 10.3 Internal API (gRPC)
**Purpose**: High-performance communication between the API Server and the Worker Service (and future Inference Runtimes).
**Implementation**: `grpcio` (Python).

*   **Why gRPC?**:
    *   **Strict Typing**: Ensures the Worker receives exactly what the API sent.
    *   **Performance**: Efficient binary serialization for internal traffic.
    *   **Streaming**: Essential for long-running jobs (e.g., streaming download progress or log updates from Worker to API).

*   **Example Worker Service**:

```protobuf
// proto/v1/worker_service.proto
service WorkerService {
  // Trigger a metadata sync
  rpc SyncMetadata(SyncMetadataRequest) returns (JobStatus);

  // Stream download progress back to the caller
  rpc DownloadArtifact(DownloadArtifactRequest) returns (stream DownloadProgress);
}
```


