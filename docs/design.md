# Model Serving Server – Design Document (v0.1)

## 0. Terminology

* **Vendor** – logical owner/namespace of the repo, e.g. `Wan-AI`, `meta-llama`, `openai`, `local`.
* **Model repo** – a repository-like bucket of related files, e.g. `Wan-AI/Wan2.2-Animate-14B`.
* **Model Artifact** – a concrete file in a repo (e.g. `model.safetensors`, `diffusion_pytorch_model.bin`, `decoder.gguf`).
* **Logical model** – something you can *run*, e.g. `"wan2.2-animate-14b:text-to-video"`, `"yolo-v8s:object-detection"`.
* **Runtime** – an engine that can execute a logical model (llama.cpp, PyTorch, TensorRT, etc.).

---

## 1. Goals & Non-goals

### Goals

1. **Single model hub** for local dev and cloud:

   * Centralized caching for HuggingFace/Modal-like repos.
   * Canonical ID: `model_vendor/model_name` (e.g. `Wan-AI/Wan2.2-Animate-14B`).

2. **Repo-structure-aware registry**:

   * Keep the *full repo structure* in metadata.
   * Parse metadata files (`config.json`, `model_index.json`, `*.json`, etc.).
   * Track which artifacts belong to which logical models.

3. **Dependency reuse**:

   * Many repos share sub-models (e.g. base models, VAE, encoder).
   * Deduplicate artifacts across repos using content hash + logical identity.
   * Use file link in local storage to avoid duplication(also verify integrity before using).

4. **Standard inference APIs**:

   * LLM/chat, embeddings, plus advanced vision/video tasks:

     * YOLO, segmentation/masks, interpolation, SR, face/pose detection, OCR, etc.

5. **Metadata in PostgreSQL**:

   * All registries, original repo, revision, local repo, model artifact metadata(e.g. file size, hash, type), jobs, etc. stored in Postgres.

6. **Logging & metrics**:

   * Structured logs for operations + errors.
   * Basic metrics (counters, histograms) derived from logs or Prometheus-style metrics.

### Non-goals

* Full multi-tenant auth/quotas.
* Complex scheduler for multi-GPU clusters.
* General-purpose training/finetuning (inference-focused).

---

## 2. High-Level Architecture

### 2.1 Service Components

1. **API Gateway / HTTP Frontend (FastAPI)**

   * Endpoints:

     * `/v1/models/*` – manage models, repos, model artifacts.
     * `/v1/llm/chat/completions`, `/v1/llm/embeddings`.
     * `/v1/tool/vision/*`, `/v1/tool/video/*`, `/v1/tool/ocr`.
   * Performs basic rate limiting, request validation.

2. **Model Registry Service**

   * Responsible for:

     * Model repo registration (`model_vendor/model_name`).
     * Repo introspection (fetch file list + metadata).
     * Mapping artifacts to logical models & tasks.
   * Backed by Postgres tables.

3. **Model Artifact Store + File Server**

   * Data path (local or remote):

     * Local dev: e.g. MODEL_STORE_URI=`file:///data/model-store/`
     * Cloud: S3/MinIO bucket + local disk cache.
   * Exposes:

     * `GET /v1/model/{model_path}/files` (local serving).
     * Internal: “give me local path for artifact X”.

4. **Worker Service (Jobs)**

   * Background tasks:

     * Repo sync (list files, metadata).
     * Model artifact download.
     * Quantization pipelines (fp16 → gguf, etc.).
     * Export/engine building (ONNX/TensorRT).
   * Uses a job queue (Redis + RQ/Celery).

5. **Inference Runtimes**

   * **LLM runtime**:

     * llama.cpp / gguf or vLLM.
   * **Vision runtime**:

     * PyTorch/ONNX/TensorRT-based pipelines for YOLO, SAM, SR, interpolation, face/pose, OCR.
     * PyTorch/ONNX/TensorRT-based pipelines for video, audio, etc.

   * Each runtime is configured to know which logical model IDs it can serve.

6. **Postgres**

   * Central metadata store.

7. **Logging & Metrics**

   * Structured logging (JSON).
   * Log sinks: console + file + Modern Logging platform. Currently SigNoz as first choice.
   * Metrics scraping: simple /v1/metrics endpoint.

---

## 3. Data Model (PostgreSQL)

Below is a first cut of the schema. Names can be adjusted, but structure covers your needs.

### 3.1 Core entities

#### `model_repo`

Represents `vendor/model_name`, e.g. `Wan-AI/Wan2.1-T2V-1.3B`.

* `id` (PK)
* `model_repo_name` - e.g. `Wan-AI/Wan2.1-T2V-1.3B`
* `model_vendor` - model_vendor name (e.g. `wan-ai`, 'meta-llama', 'openai', 'google')
* `model_name` – e.g. `"wan2.1-t2v-1.3b"`
* `source_uri` – e.g. HF repo URL or Modal URL.
* `default_branch` – `main`/`master`.
* `git_head` (nullable) – git commit hash of the default branch.
* `framework` (nullable) – e.g. `tensorflow`, `pytorch`, etc.
* `created_at`
* `updated_at`
* `deleted_at`
* `last_synced_at`
* `sync_status` – `init | sync_ready | syncing | error | completed`
* `metadata` (JSONB) – repo-level metadata.

#### `model_artifact`

Represents a file in the repository (e.g. `unet/diffusion_pytorch_model.bin`) and its local storage state.

* `id` (PK)
* `model_repo` (FK → `model_repo.id`)
* `file_path` – path in the repo (e.g. `unet/diffusion_pytorch_model.bin`)
* `file_type` – `metadata`, `model`, `tokenizer`, `config`, etc.
* `size_bytes`
* `hash_sha256` (nullable) – if known from remote metadata. Used for CAS deduplication.
* `format` - e.g. `safetensors`, `gguf`, `onnx`, `pt`, etc.
* `precision` - e.g. `fp16`, `q4_k_m`, etc.
* `storage_uri` – e.g. `file:///data/model-store/blobs/sha256/<hash>`. Shared across artifacts with same hash.
* `download_status` – `pending | downloading | completed | failed`
* `created_at`, `updated_at`
* `last_accessed_at`

**Dependency reuse**: Multiple `model_artifact` rows (from different repos) can point to the same `storage_uri` if their hashes match.

**Dependency reuse** happens because many model file can point to the same `artifact.id`.

---

### 3.2 Logical models and tasks

#### `logical_model`

User-facing “model” concept (e.g. `"wan2.1-t2v-1.3b"`).

* `id` (PK)
* `model_vendor` (FK → `model_repo.model_vendor`)
* `model_name` – internal name tag, e.g. `"wan2.1-t2v-1.3b"`
* `model_repo` (FK → `model_repo.id`)
* `category` – `llm`, `vision`, `audio`, `video`, etc.
* `sub_category` (nullable) – `base`, `lora`, `clip`,  `unet`, `vae`, `refiner`, `controlnet`, `depth`, `pose`, etc.
* `task_type` – `llm`, `text-to-image`, `text-to-video`, `image-to-video`, `image-to-image`, `video-to-video`, `object-detection`, `segmentation`, `super-resolution`, `interpolation`, `ocr`, etc.
* `preferred_format` – `gguf`, `pytorch`, `onnx`, `tensorrt`, etc.
* `preferred_precision` - preferred precision
* `available_precisions` -  list of available precisions
* `runtime_type` – `llama_cpp`, `torch`, `onnxruntime`, `tensorrt`, etc.
* `min_vram_gb` (nullable)
* `metadata` (JSONB) – full config: HF config, Wan-specific metadata, etc.
* `created_at`, `updated_at`
* `status` – `syncing | error | ready | active`

#### `model_variant`

A specific runnable configuration of a logical model (e.g. `fp16`, `q4_k_m`).

* `id` (PK)
* `logical_model_id` (FK → `logical_model.id`)
* `variant_name` – e.g. `fp16`, `q4_k_m`
* `format` – `gguf`, `pytorch`, `onnx`
* `precision` – `fp16`, `int8`, `q4_k_m`, etc.
* `size_bytes` – total size of all components
* `status` – `preparing | ready | error`
* `created_at`, `updated_at`

#### `logical_model_component`

Maps a logical part of the model (e.g. `unet`, `vae`) to a specific artifact or repo file.

*   `id` (PK)
*   `model_variant_id` (FK → `model_variant.id`)
*   `component_name` – e.g. `unet`, `vae`, `tokenizer`
*   `artifact_id` (FK → `model_artifact.id`, nullable)
*   `created_at`


---

### 3.3 Jobs, runtime instances, activity

#### `job`

Generic job record for repo sync, download, quantize.

* `id` (PK)
* `job_type` – `repo_sync`, `artifact_download`, `quantize`, `build_engine`
* `status` – `queued`, `running`, `succeeded`, `failed`
* `input` (JSONB) – job parameters.
* `output` (JSONB) – results or error info.
* `created_at`, `updated_at`, `started_at`, `finished_at`

#### `runtime_instance`

Represents a running inference process.

* `id` (PK)
* `logical_model_id` (FK → `logical_model.id`)
* `model_filename`
* `runtime_type` – `llama_cpp`, `torch`, etc.
* `host` – hostname/IP
* `gpu_index` (nullable)
* `status` – `idle`, `busy`, `error`
* `last_heartbeat_at`

#### `inference_log`

Lightweight record for logging calls.

* `id` (PK)
* `timestamp`
* `request_id`
* `user_session_id` (nullable)
* `logical_model_id` (FK)
* `model_filename`
* `runtime_instance_id` (FK)
* `task_type`
* `latency_ms`
* `input_size` (tokens/bytes/frames)
* `output_size`
* `status` – `ok`, `error`
* `error_type` (nullable)
* `error_message` (nullable)

---

## 4. Model Registration & Repo Introspection

### 4.1 Model registration API

**Request:**

```http
POST /v1/models/register
{
  "model_vendor": "Wan-AI",
  "model_name": "Wan2.1-T2V-1.3B",
  "source": {
    "provider": "huggingface",
    "repo_id": "Wan-AI/Wan2.1-T2V-1.3B",
    "revision": "main"
  },
  "task_hints": ["text-to-video"],
  "preferred_format": "gguf",
  "quantization_targets": ["q4_k_m", "q5_k_m"]
}
```

**Steps:**

1. Create or look up `model_vendor` with name `wan-ai`.
2. Create `model_repo` with `model_name = "wan2.1-t2v-1.3b"`.
3. Enqueue `job` of type `repo_sync` with payload:
   * model_vendor/model_name + provider + repo_id + revision.

### 4.2 Repo sync job (NO big weights download yet)

1. Call provider API (e.g. HuggingFace) to list files for the given revision.
2. Identify **metadata files**:

   * `config.json`, `model_index.json`, `*.yaml`, `*.json`, etc.
   * Download *only these* immediately (usually small).
   * Store them as artifacts (if you keep everything deduped) or keep in a local ephemeral cache and parse.

3. For each model file:

   * Insert `model_artifact` row:
     * `file_path`, `size`, `hash_sha256` (if known).
     * Determine `file_type` & `format` via heuristics.


4. Parse metadata and fill in:
   * `logical_model` rows.

5. Mark `model_repo.synced_at` and `sync_status = "ready"`.

At this stage:

* You know exactly what’s in the repo, how many big files exist, and which ones correspond to which logical models.
* You have *not* downloaded the big weights yet.

---

## 5. Model Download & Dependency Reuse

### 5.1 Artifact download flow

Whenever you need a big file (e.g. user wants to run `Wan2.1 T2V`):

1. Determine the `model_artifact` needed:

   * If variant is not yet created, create `model_variant` with `status = "preparing"` and enqueue `quantize`/`download` jobs.
2. For each required **artifact**:

     * Find `model_artifact` row:
       Looking for existing `model_artifact` with same `file_path` in this repo.

     * If `storage_uri` is null (not downloaded):
       1. Check if another artifact has same `hash_sha256` and `storage_uri` != null. If so, copy `storage_uri` (dedupe).
       2. Else, enqueue `artifact_download` job.

     * `artifact_download` job:
        * Download file.
        * Compute SHA256.
        * Update `storage_uri` and `download_status`.


### 5.2 Dependency reuse logic

Two reuse modes:

1. **Content-based dedupe**:

   * If 2 files (from same or different repos) have the same `hash_sha256` and same logical role (e.g. both `vae`), they reference the same `artifact`.

2. **Metadata-based reuse**:

   * Some repos may *reference* base models in metadata:

     * Example: a LoRA repo referencing `"meta-llama/Meta-Llama-3-8B"`.
   * Registry uses metadata to create `logical_model_component` entries that point at **other repo’s `model_artifact`** instead of duplicating.
   * When you need that component, you just ensure the base repo’s file is downloaded (dedupe still by hash).

---

## 6. Inference APIs and Runtime Mapping

### 6.1 LLM / chat

* **Request:**

```http
POST /v1/chat/completions
{
  "model": "Wan-AI/Wan2.1-T2V-1.3B",  // or a slug like "wan2.1-t2v-1.3b-text"
  "messages": [...],
  "stream": true
}
```

* API resolves:

  1. `vendor` & `model_name` → `model_repo`.
  2. Choose `logical_model` with `task_type = "llm"` or relevant type.
  3. Choose best `model_variant` (e.g. `gguf-q5_k_m` that fits VRAM).
  4. Ensure all variant components’ artifacts exist (trigger downloads as needed).
  5. Ask `LLM runtime` to load/use the variant.

### 6.2 Vision / video / OCR

Same pattern, different endpoints that map to appropriate `task_type`s:

* `/v1/vision/detect` → `object-detection` logical models (e.g. YOLO).
* `/v1/vision/segment` → segmentation models (SAM, etc.).
* `/v1/vision/superres` → `super-resolution`.
* `/v1/video/interpolate` → `interpolation`.
* `/v1/ocr` → OCR models.

Each logical model knows:

* Which `runtime_type` it requires.
* Which components/artifacts to load.

---

## 7. Logging & Metrics

### 7.1 Logging

Use structured logs everywhere (JSON):

* **Registry/Worker logs**:

  * events: `repo_registered`, `repo_synced`, `artifact_download_start`, `artifact_download_finish`, `quantize_start`, `quantize_finish`, `error`.
  * fields:
    * `model_repo_name`, `revision`, `job_id`, `artifact_id`, `file_path`, `hash`, `duration_ms`, `error_type`.

* **Inference logs** (to match `inference_log` table):

  * `request_id`, `model_repo_name`, `variant`, `runtime_type`, `latency_ms`, `status`, `error_type`.
  * Input/output sizes.

You can later ship logs to ClickHouse/Elastic and build dashboards.

### 7.2 Metrics

Options:

* Simple `/metrics` endpoint exposing:

  * `inference_requests_total{model_repo_name,variant,task_type,status}`
  * `inference_latency_ms_bucket{model_repo_name,variant,task_type}`
  * `artifact_download_bytes_total{source_vendor}`
  * `artifact_download_errors_total{source_vendor}`

Even if you don’t wire Prometheus now, designing log fields as above allows future aggregation.

---

## 8. Local vs Cloud Deployment

Architecture stays the same; only execution environment changes.

### 8.1 Local dev

* Docker Compose:

  * `api`, `worker`, `runtimes`, `postgres`.
  * Shared volume: `./data/model-store:/data/model-store`.
  * Shared volume: `./data/logs:/data/logs`.
  * Shared volume: `./data/cache:/data/cache`.
  * Shared volume: `./data/data-set:/data/data-set`.
  * Shared volume: `./data/tmp:/data/tmp`.
  * Shared volume: `./data/assets:/data/assets`.
* GPU placement:

  * Single 4090; runtime processes request `NVIDIA_VISIBLE_DEVICES=0`.

### 8.2 Cloud

* Kubernetes:

  * `Deployment` for API, worker.
  * `Deployment`/`StatefulSet` for runtimes with `nvidia.com/gpu: 1`.
* Artifact store:

  * Backed by S3 + local SSD cache or shared filesystem.
* Same Postgres schema; maybe managed DB service.

---

## 9. Implementation Plan (MVP)

**Phase 1 – Registry + Postgres schema**

1. Implement ORM models for:

   * `model_vendor`, `model_repo`, `model_repo_revision`, `model_artifact`, `logical_model`, `logical_model_component`, `model_variant`, `model_variant_component`, `job`.
2. Expose:

   * `POST /v1/models/register`
   * `GET /v1/models`, `GET /v1/models/{vendor}/{name}`.

**Phase 2 – Repo sync & selective metadata download**

1. Implement job worker + `repo_sync` job:

   * List files from HF.
   * Fill `model_artifact` (metadata only).
   * Download metadata files only.
   * Build `logical_model`, `logical_model_component`.
2. Implement `GET /v1/models/{vendor}/{name}/files` for debugging.

**Phase 3 – Artifact download & dedupe**

1. Implement `artifact_download` job:

   * Download big file when needed.
   * Download big file when needed.
   * sha256 → `model_artifact` dedupe (update storage_uri).
2. Optionally: `GET /v1/files/{artifact_id}` to reuse from other projects.

**Phase 4 – LLM runtime integration**

1. Hook llama.cpp (gguf) runtime.
2. Implement `/v1/chat/completions` using `logical_model + model_variant` selection.

**Phase 5 – General Vision & Audio Models (Small Models)**

1. Register repos for YOLO (vision), Face Detection (vision), and TTS/STT (audio).
2. Build logical models for `object-detection`, `face-detection`, `text-to-speech`, and `speech-to-text`.
3. Implement endpoints: `/v1/vision/detect`, `/v1/audio/speech`, `/v1/audio/transcriptions`.
4. Integrate lightweight runtimes (ONNX/PyTorch) for these tasks.

**Phase 6 – Video Generation Runtime (Wan2.1)**

1. Register Wan2.1 repo (vendor `Wan-AI`, model `Wan2.1-T2V-1.3B`).
2. Build `text-to-video` logical model.
3. Implement `/v1/video/generation` endpoint.
4. Integrate `Wan2.1` runtime (PyTorch/FlashAttn).

---

If you like this structure, next I can:

* Turn this into a repo skeleton (directory layout + `alembic` migrations + FastAPI skeleton), or
* Zoom in on the **repo sync + selective download pipeline** and write pseudo-code for the worker + Postgres operations.
