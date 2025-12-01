# Model Hub Architecture - Sync & Download Flow

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client / Admin UI                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP/REST
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Hub Service                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  API Endpoints:                                          │   │
│  │  • POST /v1/hub/register  - Register model               │   │
│  │  • POST /v1/hub/sync      - Trigger metadata sync        │   │
│  │  • POST /v1/hub/download  - Download artifacts           │   │
│  │  • GET  /v1/hub/jobs      - List jobs                    │   │
│  │  • GET  /v1/hub/models    - List models                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────┬────────────────────────────────┬───────────────────┘
             │                                │
             │ Enqueue Jobs                   │ Query/Update
             ▼                                ▼
┌─────────────────────────┐      ┌──────────────────────────────┐
│     Redis (ARQ)         │      │      PostgreSQL              │
│  ┌──────────────────┐   │      │  ┌────────────────────────┐  │
│  │  Job Queue       │   │      │  │  Tables:               │  │
│  │  • sync jobs     │   │      │  │  • model_repo          │  │
│  │  • download jobs │   │      │  │  • model_artifact      │  │
│  │  • scan jobs     │   │      │  │  • job                 │  │
│  └──────────────────┘   │      │  └────────────────────────┘  │
└────────────┬────────────┘      └──────────────┬───────────────┘
             │                                  │
             │ Dequeue                          │ Query/Update
             ▼                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Worker Service (ARQ)                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Tasks:                                                  │   │
│  │  • sync_repo_metadata()   - Fetch file list from HF      │   │
│  │  • download_artifact()    - Download files               │   │
│  │  • scan_local_storage()   - Scan local files (TODO)      │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────┬────────────────────────────────┬───────────────────┘
             │                                │
             │ API Calls                      │ File I/O
             ▼                                ▼
┌─────────────────────────┐      ┌──────────────────────────────┐
│  HuggingFace Hub        │      │  Local File Storage          │
│  ┌──────────────────┐   │      │  /data/model-store/          │
│  │  • File lists    │   │      │  ├── blobs/sha256/           │
│  │  • Metadata      │   │      │  │   └── <hash>  (CAS)       │
│  │  • Model files   │   │      │  ├── metadata/               │
│  └──────────────────┘   │      │  │   └── <repo>/             │
└─────────────────────────┘      │  └── temp/                   │
                                 └──────────────────────────────┘
```

## Data Flow: Metadata Sync

```
1. User Request
   POST /v1/hub/sync {"repo_id": "Wan-AI/Wan2.1-T2V-1.3B"}
   │
   ▼
2. API Creates Job
   ┌─────────────────────────────────────┐
   │ Job Record in PostgreSQL            │
   │ • type: "sync"                      │
   │ • status: "pending"                 │
   │ • payload: {"repo_id": "..."}       │
   └─────────────────────────────────────┘
   │
   ▼
3. Enqueue to Redis
   ┌─────────────────────────────────────┐
   │ ARQ Job Queue                       │
   │ sync_repo_metadata(repo_id, job_id) │
   └─────────────────────────────────────┘
   │
   ▼
4. Worker Processes Job
   ┌─────────────────────────────────────┐
   │ a. Update job status: "running"     │
   │ b. Call HF API: list files          │
   │ c. For each file:                   │
   │    • Create ModelArtifact record    │
   │    • If metadata file (< 10MB):     │
   │      - Download immediately         │
   │      - Store in metadata/           │
   │ d. Update ModelRepo: "synced"       │
   │ e. Update job status: "completed"   │
   └─────────────────────────────────────┘
   │
   ▼
5. Result
   ┌─────────────────────────────────────┐
   │ Database State:                     │
   │ • ModelRepo.status = "synced"       │
   │ • 40+ ModelArtifact records         │
   │ • Job.status = "completed"          │
   │ • Metadata files downloaded         │
   └─────────────────────────────────────┘
```

## Data Flow: File Download

```
1. User Request
   POST /v1/hub/download {"artifact_ids": ["uuid1", "uuid2"]}
   │
   ▼
2. API Validates & Enqueues
   ┌─────────────────────────────────────┐
   │ For each artifact_id:               │
   │ • Verify artifact exists            │
   │ • Create Job record                 │
   │ • Enqueue download_artifact task    │
   └─────────────────────────────────────┘
   │
   ▼
3. Worker Downloads File
   ┌─────────────────────────────────────┐
   │ a. Update artifact: "downloading"   │
   │ b. Download from HF to temp/        │
   │ c. Compute SHA256 hash              │
   │ d. Check if hash exists in blobs/   │
   │    • If yes: delete temp, link      │
   │    • If no: move to blobs/<hash>    │
   │ e. Update artifact:                 │
   │    • local_path = blobs/<hash>      │
   │    • content_hash = <hash>          │
   │    • status = "completed"           │
   └─────────────────────────────────────┘
   │
   ▼
4. Result
   ┌─────────────────────────────────────┐
   │ File Storage:                       │
   │ /data/model-store/blobs/sha256/     │
   │   abc123...  (deduplicated)         │
   │                                     │
   │ Database:                           │
   │ • ModelArtifact.local_path set      │
   │ • ModelArtifact.status = "completed"│
   │ • Job.status = "completed"          │
   └─────────────────────────────────────┘
```

## Key Design Decisions

### 1. Content-Addressable Storage (CAS)
- Files stored by SHA256 hash
- Automatic deduplication
- Multiple artifacts can reference same file
- Integrity verification built-in

### 2. Two-Phase Download
- **Phase 1 (Sync)**: Metadata only, small files
- **Phase 2 (Download)**: Large model files on-demand
- Reduces initial sync time
- Allows selective downloads

### 3. Async Job Processing
- Non-blocking API responses
- Background processing with ARQ
- Job status tracking
- Scalable to multiple workers

### 4. Database-First Design
- PostgreSQL as source of truth
- File system is cache/storage layer
- Easy to query and monitor
- Supports future features (quotas, permissions)

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| API | FastAPI | REST endpoints |
| Worker | ARQ | Async task queue |
| Database | PostgreSQL | Metadata storage |
| Queue | Redis | Job queue |
| Storage | Local FS | File storage |
| Client | HuggingFace Hub | Model source |
| HTTP | httpx | Async HTTP client |
| ORM | SQLModel | Database models |

## Scalability Considerations

### Current (Local Dev)
- Single API instance
- Single worker instance
- Local file system
- Suitable for 1-10 users

### Future (Cloud)
- Multiple API instances (load balanced)
- Multiple worker instances (horizontal scaling)
- S3/MinIO for storage
- Distributed Redis
- Suitable for 100+ users
