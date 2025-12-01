# Model Hub API - Sync and Download Implementation

This document describes the newly implemented metadata sync and model file download functionality for the Model Hub.

## Overview

The Model Hub now supports:
1. **Metadata Sync**: Fetch repository file lists from HuggingFace and create artifact records
2. **File Download**: Download model files with content-addressable storage and deduplication
3. **Job Management**: Asynchronous background job processing with ARQ

## Architecture

### Components

1. **HFClient** (`src/common/hf_client.py`)
   - Interacts with HuggingFace Hub API
   - Lists repository files
   - Downloads files with resume capability
   - Computes SHA256 hashes
   - Classifies file types (model, config, tokenizer)

2. **Worker Tasks** (`src/worker_service/tasks.py`)
   - `sync_repo_metadata`: Syncs metadata from HuggingFace
   - `download_artifact`: Downloads individual model files
   - `scan_local_storage`: Scans local storage (TODO)

3. **Job Queue** (`src/common/job_queue.py`)
   - Enqueues jobs to ARQ (Redis-based task queue)
   - Creates job records in database
   - Tracks job status

4. **API Endpoints** (`src/hub_service/api.py`)
   - `POST /v1/hub/register`: Register a model repository
   - `POST /v1/hub/sync`: Trigger metadata sync
   - `POST /v1/hub/download`: Download specific artifacts
   - `GET /v1/hub/jobs`: List jobs
   - `GET /v1/hub/jobs/{job_id}`: Get job details

## API Usage

### 1. Register a Model

```bash
curl -X POST http://localhost:8000/v1/hub/register \
  -H "Content-Type: application/json" \
  -d '{
    "vendor": "Wan-AI",
    "name": "Wan2.1-T2V-1.3B",
    "source_repo_id": "Wan-AI/Wan2.1-T2V-1.3B",
    "auto_sync": true
  }'
```

Response:
```json
{
  "id": "uuid",
  "vendor": "Wan-AI",
  "name": "Wan2.1-T2V-1.3B",
  "repo_id": "Wan-AI/Wan2.1-T2V-1.3B",
  "status": "registered",
  "created_at": "2025-12-01T00:00:00",
  "updated_at": "2025-12-01T00:00:00"
}
```

If `auto_sync` is `true`, a sync job is automatically queued.

### 2. Trigger Metadata Sync

```bash
curl -X POST http://localhost:8000/v1/hub/sync \
  -H "Content-Type: application/json" \
  -d '{
    "repo_id": "Wan-AI/Wan2.1-T2V-1.3B"
  }'
```

Response:
```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Sync job queued"
}
```

**What happens during sync:**
1. Fetches file list from HuggingFace
2. Creates `ModelArtifact` records for each file
3. Downloads small metadata files (< 10MB) immediately
4. Updates `ModelRepo` status to "synced"

### 3. Download Artifacts

```bash
curl -X POST http://localhost:8000/v1/hub/download \
  -H "Content-Type: application/json" \
  -d '{
    "artifact_ids": ["uuid1", "uuid2"]
  }'
```

Response:
```json
{
  "job_id": "uuid",
  "status": "pending",
  "message": "Queued 2 download job(s)"
}
```

**What happens during download:**
1. Downloads file from HuggingFace
2. Computes SHA256 hash
3. Stores in content-addressable storage (`/data/model-store/blobs/sha256/<hash>`)
4. Deduplicates if file already exists
5. Updates `ModelArtifact` record with local path

### 4. Check Job Status

```bash
curl http://localhost:8000/v1/hub/jobs/{job_id}
```

Response:
```json
{
  "id": "uuid",
  "type": "sync",
  "status": "completed",
  "payload": {"repo_id": "Wan-AI/Wan2.1-T2V-1.3B"},
  "logs": "Synced 42 files, created 40 new artifacts, downloaded 2 metadata files",
  "created_at": "2025-12-01T00:00:00",
  "updated_at": "2025-12-01T00:01:00"
}
```

### 5. List All Jobs

```bash
curl http://localhost:8000/v1/hub/jobs
```

## Storage Structure

```
/data/model-store/
├── blobs/
│   └── sha256/
│       ├── abc123...  # Content-addressable storage
│       └── def456...
├── metadata/
│   └── Wan-AI_Wan2.1-T2V-1.3B/
│       ├── config.json
│       └── model_index.json
└── temp/
    └── (temporary download files)
```

## Configuration

Environment variables (`.env`):

```env
DATABASE_URL=postgresql+asyncpg://hub_user:hub_password@localhost:5432/model_hub
REDIS_URL=redis://localhost:6379
MODEL_STORE_PATH=/data/model-store
HF_TOKEN=your_huggingface_token_here  # Optional for public repos
```

## Running the Services

### 1. Start the API Server

```bash
cd /media/yuechuan/warehouse/model-serving/bento_server
uv run uvicorn src.hub_service.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Start the Worker

```bash
cd /media/yuechuan/warehouse/model-serving/bento_server
uv run arq src.worker_service.main.WorkerSettings
```

### 3. Start Redis (if not running)

```bash
docker-compose up -d redis
```

### 4. Run Database Migrations

```bash
uv run alembic upgrade head
```

## Testing

Run the manual test script:

```bash
uv run python tests/test_api_manual.py
```

This will:
1. Register a model
2. List models
3. Trigger a sync job
4. Check job status
5. List all jobs

## Features

### ✅ Implemented

- [x] HuggingFace client for repository metadata
- [x] Metadata sync task
- [x] Artifact download task with SHA256 verification
- [x] Content-addressable storage with deduplication
- [x] Job queue with ARQ
- [x] API endpoints for sync and download
- [x] Job status tracking
- [x] Automatic metadata file download during sync

### 🚧 TODO

- [ ] Local storage scan implementation
- [ ] Resume partial downloads
- [ ] Progress tracking for large downloads
- [ ] Batch download optimization
- [ ] Webhook notifications for job completion
- [ ] Admin UI for job monitoring

## Data Model

### ModelRepo
- Represents a HuggingFace repository
- Status: `registered` → `synced` → `error`

### ModelArtifact
- Represents a file in the repository
- Download status: `pending` → `downloading` → `completed` / `failed`
- Stores local path and content hash

### Job
- Tracks background tasks
- Types: `sync`, `download`, `scan`
- Status: `pending` → `running` → `completed` / `failed`

## Error Handling

- Jobs that fail update their status to `failed` with error logs
- Artifacts that fail to download are marked as `failed`
- API returns appropriate HTTP status codes (404, 400, 500)

## Next Steps

1. Implement local storage scanning
2. Add progress tracking for downloads
3. Build admin UI for job monitoring
4. Add tests for edge cases
5. Implement retry logic for failed downloads
6. Add metrics and monitoring
