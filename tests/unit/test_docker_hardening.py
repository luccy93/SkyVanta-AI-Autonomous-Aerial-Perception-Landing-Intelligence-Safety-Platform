"""Unit tests for Docker container hardening, multi-stage build, and deployment configuration."""

from pathlib import Path
import pytest
import yaml

from skyvanta.deployment.config import DeploymentConfig, DeploymentEnvironment
from skyvanta.deployment.health import HealthCheckService


@pytest.fixture
def repo_root() -> Path:
    """Returns absolute path to the repository root directory."""
    return Path(__file__).resolve().parent.parent.parent


def test_dockerfile_exists_and_multistage(repo_root):
    """1. Dockerfile exists and implements a multi-stage build pattern."""
    dockerfile_path = repo_root / "Dockerfile"
    assert dockerfile_path.is_file(), "Dockerfile must exist at repository root"

    content = dockerfile_path.read_text(encoding="utf-8")
    assert "AS builder" in content, "Dockerfile must define builder stage"
    assert "AS runtime" in content, "Dockerfile must define runtime stage"
    assert "python:3.11-slim" in content, "Dockerfile must use Python 3.11-slim base"


def test_dockerfile_non_root_user(repo_root):
    """2. Dockerfile configures an unprivileged user (skyvanta)."""
    content = (repo_root / "Dockerfile").read_text(encoding="utf-8")
    assert "useradd" in content and "skyvanta" in content, "Must create skyvanta user"
    assert "USER skyvanta" in content, "Must switch to non-root user before execution"


def test_dockerfile_port_and_healthcheck(repo_root):
    """3. Dockerfile exposes port 8080 and defines a container HEALTHCHECK."""
    content = (repo_root / "Dockerfile").read_text(encoding="utf-8")
    assert "EXPOSE 8080" in content, "Must expose standard application port 8080"
    assert "HEALTHCHECK" in content, "Must define container HEALTHCHECK"
    assert "HealthCheckService" in content, "HEALTHCHECK must evaluate HealthCheckService"


def test_dockerfile_exec_form_cmd_no_reload(repo_root):
    """4. Dockerfile uses direct exec-form CMD without development reload."""
    content = (repo_root / "Dockerfile").read_text(encoding="utf-8")
    assert 'CMD ["uvicorn", "skyvanta.deployment.api.app:app"' in content, "CMD must be exec-form"
    assert "--reload" not in content, "Production CMD must not include --reload"


def test_dockerfile_oci_metadata_labels(repo_root):
    """5. Dockerfile includes standard OCI metadata labels."""
    content = (repo_root / "Dockerfile").read_text(encoding="utf-8")
    assert "org.opencontainers.image.title" in content
    assert "org.opencontainers.image.version" in content
    assert "org.opencontainers.image.licenses" in content


def test_dockerignore_secret_and_artifact_exclusions(repo_root):
    """6. .dockerignore excludes git, caches, test files, secrets, and logs."""
    dockerignore_path = repo_root / ".dockerignore"
    assert dockerignore_path.is_file(), ".dockerignore must exist"

    content = dockerignore_path.read_text(encoding="utf-8")
    required_exclusions = [
        ".git",
        "tests",
        "__pycache__",
        ".env",
        "*.key",
        "*.token",
        "credentials",
        ".pytest_cache",
    ]
    for pattern in required_exclusions:
        assert pattern in content, f".dockerignore must exclude '{pattern}'"


def test_compose_file_structure_and_security(repo_root):
    """7. compose.yaml specifies hardened security options and environment."""
    compose_path = repo_root / "compose.yaml"
    assert compose_path.is_file(), "compose.yaml must exist"

    with open(compose_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "services" in data
    assert "skyvanta-api" in data["services"]
    service = data["services"]["skyvanta-api"]
    assert "8080:8080" in service["ports"]
    assert "security_opt" in service
    assert any("no-new-privileges:true" in opt for opt in service["security_opt"])


def test_container_healthcheck_command_execution():
    """8. Healthcheck command executed directly evaluates service as healthy."""
    service = HealthCheckService()
    res = service.check_health()
    assert res.status.value == "healthy"
    assert res.hardware_access is False
    assert res.network_model_download is False
    assert res.safety_boundary_enforced is True


def test_production_environment_safety_defaults():
    """9. Production DeploymentConfig enforces immutable simulation-only safety defaults."""
    cfg = DeploymentConfig(environment=DeploymentEnvironment.PRODUCTION)
    assert cfg.allow_external is False
    assert cfg.allow_network_download is False
    assert cfg.hardware_disconnected is True
    assert cfg.port == 8080
