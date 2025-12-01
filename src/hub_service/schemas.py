from pydantic import BaseModel


class RegisterModelRequest(BaseModel):
    vendor: str
    name: str
    source_repo_id: str


class ListModelsResponse(BaseModel):
    models: list
    total_count: int
