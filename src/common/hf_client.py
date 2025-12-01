"""HuggingFace Hub client for fetching repository metadata and files."""

import hashlib
from pathlib import Path
from typing import Any

import httpx
from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import HfHubHTTPError

from src.common.config import settings


class HFClient:
    """Client for interacting with HuggingFace Hub."""

    def __init__(self, token: str | None = None):
        """Initialize HF client.

        Args:
            token: HuggingFace API token (optional for public repos)
        """
        self.token = token or settings.hf_token
        self.api = HfApi(token=self.token)

    async def list_repo_files(
        self, repo_id: str, revision: str = "main"
    ) -> list[dict[str, Any]]:
        """List all files in a HuggingFace repository.

        Args:
            repo_id: Repository ID (e.g., "Wan-AI/Wan2.1-T2V-1.3B")
            revision: Git revision (branch, tag, or commit hash)

        Returns:
            List of file metadata dictionaries with keys:
                - path: str (file path in repo)
                - size: int (file size in bytes)
                - blob_id: str (Git blob ID)
                - lfs: dict | None (LFS metadata if applicable)
        """
        try:
            # Get repo info with file details
            repo_info = self.api.repo_info(
                repo_id=repo_id, revision=revision, files_metadata=True
            )

            files = []
            for sibling in repo_info.siblings:
                file_info = {
                    "path": sibling.rfilename,
                    "size": sibling.size or 0,
                    "blob_id": sibling.blob_id or "",
                    "lfs": sibling.lfs if hasattr(sibling, "lfs") else None,
                }
                files.append(file_info)

            return files

        except HfHubHTTPError as e:
            raise ValueError(f"Failed to list files for {repo_id}: {e}") from e

    async def get_file_metadata(
        self, repo_id: str, file_path: str, revision: str = "main"
    ) -> dict[str, Any]:
        """Get metadata for a specific file in the repository.

        Args:
            repo_id: Repository ID
            file_path: Path to file in repository
            revision: Git revision

        Returns:
            File metadata dictionary
        """
        try:
            # Use HF API to get file info
            url = f"https://huggingface.co/{repo_id}/resolve/{revision}/{file_path}"
            async with httpx.AsyncClient() as client:
                response = await client.head(
                    url,
                    headers={"Authorization": f"Bearer {self.token}"}
                    if self.token
                    else {},
                    follow_redirects=True,
                )
                response.raise_for_status()

                return {
                    "path": file_path,
                    "size": int(response.headers.get("Content-Length", 0)),
                    "etag": response.headers.get("ETag", "").strip('"'),
                    "content_type": response.headers.get("Content-Type", ""),
                }

        except httpx.HTTPError as e:
            raise ValueError(
                f"Failed to get metadata for {file_path} in {repo_id}: {e}"
            ) from e

    async def download_file(
        self,
        repo_id: str,
        file_path: str,
        local_dir: Path,
        revision: str = "main",
        resume: bool = True,
    ) -> Path:
        """Download a file from HuggingFace repository.

        Args:
            repo_id: Repository ID
            file_path: Path to file in repository
            local_dir: Local directory to save the file
            revision: Git revision
            resume: Whether to resume partial downloads

        Returns:
            Path to downloaded file
        """
        try:
            # Ensure local directory exists
            local_dir.mkdir(parents=True, exist_ok=True)

            # Download using hf_hub_download
            downloaded_path = hf_hub_download(
                repo_id=repo_id,
                filename=file_path,
                revision=revision,
                cache_dir=str(local_dir),
                token=self.token,
                resume_download=resume,
            )

            return Path(downloaded_path)

        except Exception as e:
            raise ValueError(
                f"Failed to download {file_path} from {repo_id}: {e}"
            ) from e

    async def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            SHA256 hash as hex string
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def classify_file_type(self, file_path: str) -> str:
        """Classify file type based on path and extension.

        Args:
            file_path: Path to file in repository

        Returns:
            File type: "model", "config", "tokenizer", or "other"
        """
        path_lower = file_path.lower()

        # Model files
        model_extensions = {
            ".safetensors",
            ".bin",
            ".pt",
            ".pth",
            ".gguf",
            ".onnx",
            ".pb",
        }
        if any(path_lower.endswith(ext) for ext in model_extensions):
            return "model"

        # Config files
        if "config" in path_lower and path_lower.endswith(".json"):
            return "config"

        # Tokenizer files
        if "tokenizer" in path_lower or "vocab" in path_lower:
            return "tokenizer"

        return "other"

    def infer_format_and_precision(
        self, file_path: str
    ) -> tuple[str | None, str | None]:
        """Infer model format and precision from file path.

        Args:
            file_path: Path to file in repository

        Returns:
            Tuple of (format, precision)
        """
        path_lower = file_path.lower()

        # Format detection
        format_map = {
            ".safetensors": "safetensors",
            ".gguf": "gguf",
            ".onnx": "onnx",
            ".bin": "pytorch",
            ".pt": "pytorch",
            ".pth": "pytorch",
            ".pb": "tensorflow",
        }

        file_format = None
        for ext, fmt in format_map.items():
            if path_lower.endswith(ext):
                file_format = fmt
                break

        # Precision detection (heuristic)
        precision = None
        if "fp16" in path_lower or "f16" in path_lower:
            precision = "fp16"
        elif "fp32" in path_lower or "f32" in path_lower:
            precision = "fp32"
        elif "bf16" in path_lower:
            precision = "bf16"
        elif "int8" in path_lower or "q8" in path_lower:
            precision = "int8"
        elif "q4" in path_lower:
            precision = "q4"
        elif "q5" in path_lower:
            precision = "q5"
        elif "q6" in path_lower:
            precision = "q6"

        return file_format, precision
