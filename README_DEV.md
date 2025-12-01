# Development Guide

This guide covers how to set up, run, and develop the **Model Hub** project locally.

## 1. Prerequisites

Ensure you have the following installed:

*   **OS**: Linux (recommended) or macOS.
*   **Python**: 3.12+
*   **Docker & Docker Compose**: For running infrastructure (Postgres, Redis, SigNoz).
*   **Node.js & npm**: For installing the `buf` CLI.
*   **uv**: Python package manager (`pip install uv`).

## 2. Initial Setup

### 2.1. Install Dependencies

1.  **Python Dependencies**:
    ```bash
    uv sync
    ```

2.  **Buf CLI** (for Protobuf management):
    ```bash
    npm install -g @bufbuild/buf
    ```

### 2.2. Start Infrastructure

We use Docker Compose to run PostgreSQL, Redis, and the SigNoz observability stack.

```bash
docker-compose up -d
```

This will start:
*   **Infra**: PostgreSQL (5432) & Redis (6379) in a single container.
*   **SigNoz**: ClickHouse, ZooKeeper, Query Service, Frontend, and OTEL Collector.

**Verify Infrastructure**:
*   **SigNoz Dashboard**: [http://localhost:3301](http://localhost:3301)
*   **ClickHouse**: [http://localhost:8124](http://localhost:8124)

### 2.3. Database Migrations

Initialize the database schema using Alembic:

```bash
uv run alembic upgrade head
```

## 3. Running Services

You need to run the API Service and the Worker Service in separate terminal windows.

### 3.1. Hub API Service

Runs the FastAPI application.

```bash
uv run uvicorn src.hub_service.main:app --reload --port 8001
```
*   **Health Check**: [http://localhost:8001/health](http://localhost:8001/health)
*   **API Docs**: [http://localhost:8001/docs](http://localhost:8001/docs)

### 3.2. Worker Service

Runs the ARQ worker for background tasks (sync, download, scan).

```bash
uv run arq src.worker_service.main.WorkerSettings
```

## 4. Development Workflow

### 4.1. Protobuf & gRPC

We use **Buf** to manage Protobuf definitions in `proto/v1`.

*   **Linting**:
    ```bash
    buf lint
    ```
*   **Breaking Change Detection**:
    ```bash
    buf breaking --against '.git#branch=main'
    ```
*   **Code Generation** (Future):
    Currently, we are manually mapping schemas. In the future, we will use `buf generate` to create Python code.

### 4.2. Linting & Formatting

We use **Ruff** for linting and formatting, and **Mypy** for type checking.

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check . --fix

# Type check
uv run mypy .
```

### 4.3. Testing

Run the test suite with Pytest:

```bash
uv run pytest
```

## 5. Troubleshooting

### Ports in Use
If you see "Address already in use" errors:
*   **8000/8001**: Change the uvicorn port.
*   **5432/6379**: Ensure no local Postgres/Redis is running, or stop them.
*   **3301/8080/4317**: Check if another SigNoz instance or service is running.

### SigNoz Issues
If SigNoz services fail to start (e.g., "Database does not exist"):
1.  Check `signoz-schema-migrator` logs:
    ```bash
    docker logs signoz-schema-migrator
    ```
2.  Restart the stack:
    ```bash
    docker-compose restart
    ```

### Database Connection
The services connect to `localhost` by default.
*   **URL**: `postgresql+asyncpg://hub_user:hub_password@localhost:5432/model_hub`
*   **Redis**: `redis://localhost:6379`

If running *inside* Docker, use `infra` as the hostname instead of `localhost`.
