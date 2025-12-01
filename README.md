# Model Hub

Local-first Model Hub for managing ML models.

## Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Node.js & npm (for Buf and Frontend)

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install uv
    uv sync
    # OR
    pip install -r requirements.txt # (Generate this if needed)
    ```

2.  **Start Infrastructure**:
    ```bash
    docker-compose up -d
    ```

3.  **Run Migrations**:
    ```bash
    alembic upgrade head
    ```

4.  **Start API Service**:
    ```bash
    uvicorn src.hub_service.main:app --reload
    ```

5.  **Start Worker Service**:
    ```bash
    arq src.worker_service.main.WorkerSettings
    ```

## Development

-   **Linting**: `ruff check .`
-   **Type Checking**: `mypy .`
-   **Testing**: `pytest`

## Project Structure

-   `src/hub_service`: FastAPI application.
-   `src/worker_service`: ARQ worker for background tasks.
-   `src/common`: Shared models, config, and DB logic.
-   `proto`: Protocol Buffer definitions.

## Known Issues

### TODO: SigNoz Log Integration

**Issue**: SigNoz log collection is currently not working properly.

**Status**: Known issue, pending investigation and fix.

**Details**:
- SigNoz services (clickhouse, zookeeper, signoz-unified, otel-collector) are running in docker-compose
- Metrics and traces may be working, but log ingestion is not functional
- Application logs are not being properly forwarded to SigNoz

**Workaround**: Use local console/file logging for now.

**Next Steps**:
1. Verify OTLP log exporter configuration in `otel-collector-config.yaml`
2. Check application log handler configuration in `src/common/config.py`
3. Review SigNoz logs for any ingestion errors
4. Test log forwarding with simple test messages
