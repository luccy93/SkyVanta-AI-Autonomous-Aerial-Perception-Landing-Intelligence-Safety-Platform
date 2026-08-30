"""Release manifest metadata model, Git SHA discovery, and packaging contracts."""

from datetime import datetime, timezone
import json
import os
import platform
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, Field

try:
    import importlib.metadata as importlib_metadata
    __version__ = importlib_metadata.version("skyvanta")
except Exception:
    __version__ = "0.1.0"


def detect_git_metadata(base_dir: Optional[str] = None) -> Tuple[str, str]:
    """Safely discovers Git commit SHA and branch name without subprocess execution.

    Discovery Priority:
    1. Direct environment variable overrides (SKYVANTA_GIT_SHA, GIT_COMMIT, RENDER_GIT_COMMIT, GITHUB_SHA).
    2. Direct branch environment variables (SKYVANTA_GIT_BRANCH, GIT_BRANCH, GITHUB_REF_NAME).
    3. Packaged build manifest (release-manifest.json).
    4. Pure Python .git/HEAD file inspection.
    5. Safe fallback: ("unknown", "unknown").

    Returns:
        Tuple of (git_commit_sha, git_branch_name).
    """
    git_commit = "unknown"
    git_branch = "unknown"

    # 1. Environment variable inspection for commit SHA
    env_sha = (
        os.getenv("SKYVANTA_GIT_SHA")
        or os.getenv("GIT_COMMIT")
        or os.getenv("RENDER_GIT_COMMIT")
        or os.getenv("GITHUB_SHA")
        or os.getenv("SOURCE_VERSION")
    )
    if env_sha and env_sha.strip():
        git_commit = env_sha.strip()[:40]

    # 2. Environment variable inspection for branch name
    env_branch = (
        os.getenv("SKYVANTA_GIT_BRANCH")
        or os.getenv("GIT_BRANCH")
        or os.getenv("RENDER_GIT_BRANCH")
        or os.getenv("GITHUB_REF_NAME")
    )
    if env_branch and env_branch.strip():
        git_branch = env_branch.strip()

    # If both commit and branch are resolved, return immediately
    if git_commit != "unknown" and git_branch != "unknown":
        return git_commit, git_branch

    # 3. Check packaged release-manifest.json in base directory
    root_path = base_dir or os.getcwd()
    manifest_path = os.path.join(root_path, "release-manifest.json")
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if git_commit == "unknown" and data.get("git_commit"):
                    git_commit = str(data["git_commit"]).strip()[:40]
                if git_branch == "unknown" and data.get("git_branch"):
                    git_branch = str(data["git_branch"]).strip()
        except Exception:
            pass

    if git_commit != "unknown" and git_branch != "unknown":
        return git_commit, git_branch

    # 4. Pure Python .git/HEAD reader (non-intrusive, zero subprocess/shell)
    try:
        git_dir = os.path.join(root_path, ".git")
        head_file = os.path.join(git_dir, "HEAD")
        if os.path.isfile(head_file):
            with open(head_file, "r", encoding="utf-8") as f:
                head_content = f.read().strip()

            if head_content.startswith("ref:"):
                ref_relative = head_content[4:].strip()
                if git_branch == "unknown":
                    # e.g. refs/heads/main -> main
                    git_branch = ref_relative.split("/")[-1] if "/" in ref_relative else ref_relative

                if git_commit == "unknown":
                    ref_file = os.path.join(git_dir, ref_relative.replace("/", os.sep))
                    if os.path.isfile(ref_file):
                        with open(ref_file, "r", encoding="utf-8") as rf:
                            git_commit = rf.read().strip()[:40]
                    else:
                        # Check packed-refs
                        packed_file = os.path.join(git_dir, "packed-refs")
                        if os.path.isfile(packed_file):
                            with open(packed_file, "r", encoding="utf-8") as pf:
                                for line in pf:
                                    if ref_relative in line and not line.startswith("#"):
                                        git_commit = line.split()[0].strip()[:40]
                                        break
            elif len(head_content) >= 7 and git_commit == "unknown":
                git_commit = head_content[:40]
                if git_branch == "unknown":
                    git_branch = "detached-head"
    except Exception:
        pass

    return git_commit, git_branch


class ReleaseManifest(BaseModel):
    """Immutable production release manifest metadata model."""

    application_name: str = Field(
        default="SkyVanta AI",
        description="Application brand and platform identifier.",
    )
    version: str = Field(
        default_factory=lambda: __version__,
        description="Semantic application release version string.",
    )
    api_version: str = Field(
        default="v1",
        description="REST and WebSocket API specification version.",
    )
    git_commit: str = Field(
        default="unknown",
        description="Deterministic Git commit SHA-1 identifier.",
    )
    git_branch: str = Field(
        default="unknown",
        description="Active Git branch identifier.",
    )
    build_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC ISO-8601 release build and packaging timestamp.",
    )
    python_version: str = Field(
        default_factory=lambda: platform.python_version(),
        description="Host runtime Python environment version.",
    )
    deployment_environment: str = Field(
        default="production",
        description="Deployment target tier (development, testing, production).",
    )
    docker_image: str = Field(
        default="skyvanta-ai:latest",
        description="Canonical Docker container image tag.",
    )
    core_architecture_version: str = Field(
        default="V1-V9",
        description="Frozen robotics core architecture milestone.",
    )
    test_count: int = Field(
        default=399,
        ge=0,
        description="Verified regression test suite baseline count.",
    )
    hardware_access: bool = Field(
        default=False,
        description="Hardware connectivity status (strictly False).",
    )
    network_model_download: bool = Field(
        default=False,
        description="Runtime network model download capability (strictly False).",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes manifest to a sanitized dictionary."""
        return self.model_dump()

    def to_json(self, indent: int = 2) -> str:
        """Serializes manifest to formatted JSON."""
        return json.dumps(self.to_dict(), indent=indent)

    def save_to_file(self, target_path: str) -> None:
        """Writes release manifest to JSON file."""
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(self.to_json(indent=2) + "\n")

    @classmethod
    def from_file(cls, manifest_path: str) -> "ReleaseManifest":
        """Loads and parses a release manifest from a JSON file."""
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    @classmethod
    def generate(
        cls,
        environment: str = "production",
        docker_image: Optional[str] = None,
        test_count: int = 399,
        base_dir: Optional[str] = None,
    ) -> "ReleaseManifest":
        """Generates a fresh release manifest capturing current environment metadata."""
        sha, branch = detect_git_metadata(base_dir=base_dir)
        image = docker_image or os.getenv("SKYVANTA_DOCKER_IMAGE", "skyvanta-ai:latest")
        timestamp = os.getenv("BUILD_TIMESTAMP") or datetime.now(timezone.utc).isoformat()

        return cls(
            application_name="SkyVanta AI",
            version=__version__,
            api_version="v1",
            git_commit=sha,
            git_branch=branch,
            build_timestamp=timestamp,
            python_version=platform.python_version(),
            deployment_environment=environment,
            docker_image=image,
            core_architecture_version="V1-V9",
            test_count=test_count,
            hardware_access=False,
            network_model_download=False,
        )
