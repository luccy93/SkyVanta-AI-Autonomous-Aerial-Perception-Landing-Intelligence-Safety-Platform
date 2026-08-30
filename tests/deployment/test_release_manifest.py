"""Unit tests for ReleaseManifest and Git SHA detection."""

import json
import os
import tempfile
import pytest

from skyvanta.deployment.release.manifest import (
    ReleaseManifest,
    detect_git_metadata,
)


def test_release_manifest_defaults():
    """Verifies default release manifest fields and safety flags."""
    manifest = ReleaseManifest()
    assert manifest.application_name == "SkyVanta AI"
    assert manifest.version == "0.1.0"
    assert manifest.api_version == "v1"
    assert manifest.core_architecture_version == "V1-V9"
    assert manifest.hardware_access is False
    assert manifest.network_model_download is False
    assert manifest.test_count >= 399


def test_release_manifest_serialization():
    """Verifies JSON serialization and round-trip parsing."""
    manifest = ReleaseManifest(
        version="0.1.0",
        git_commit="abcdef1234567890abcdef1234567890abcdef12",
        git_branch="main",
        deployment_environment="production",
    )
    json_str = manifest.to_json()
    assert "abcdef1234567890" in json_str
    assert '"hardware_access": false' in json_str

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".json") as f:
        temp_path = f.name

    try:
        manifest.save_to_file(temp_path)
        loaded = ReleaseManifest.from_file(temp_path)
        assert loaded.version == manifest.version
        assert loaded.git_commit == manifest.git_commit
        assert loaded.git_branch == manifest.git_branch
        assert loaded.hardware_access is False
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_git_detection_from_env_sha(monkeypatch):
    """Verifies git detection prioritizes injected environment variable SKYVANTA_GIT_SHA."""
    test_sha = "1234567890abcdef1234567890abcdef12345678"
    test_branch = "release-v0.1.0"
    monkeypatch.setenv("SKYVANTA_GIT_SHA", test_sha)
    monkeypatch.setenv("SKYVANTA_GIT_BRANCH", test_branch)

    sha, branch = detect_git_metadata()
    assert sha == test_sha
    assert branch == test_branch


def test_git_detection_from_render_env(monkeypatch):
    """Verifies fallback to RENDER_GIT_COMMIT when SKYVANTA_GIT_SHA is absent."""
    monkeypatch.delenv("SKYVANTA_GIT_SHA", raising=False)
    monkeypatch.delenv("GIT_COMMIT", raising=False)
    test_sha = "render1234567890abcdef1234567890abcdef12"
    monkeypatch.setenv("RENDER_GIT_COMMIT", test_sha)

    sha, _ = detect_git_metadata()
    assert sha == test_sha


def test_git_detection_fallback(monkeypatch):
    """Verifies safe fallback to 'unknown' when no Git metadata is discoverable."""
    monkeypatch.delenv("SKYVANTA_GIT_SHA", raising=False)
    monkeypatch.delenv("GIT_COMMIT", raising=False)
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.delenv("SOURCE_VERSION", raising=False)
    monkeypatch.delenv("SKYVANTA_GIT_BRANCH", raising=False)
    monkeypatch.delenv("GIT_BRANCH", raising=False)
    monkeypatch.delenv("RENDER_GIT_BRANCH", raising=False)
    monkeypatch.delenv("GITHUB_REF_NAME", raising=False)

    with tempfile.TemporaryDirectory() as empty_dir:
        sha, branch = detect_git_metadata(base_dir=empty_dir)
        assert sha == "unknown"
        assert branch == "unknown"


def test_release_manifest_generate():
    """Verifies ReleaseManifest.generate factory method."""
    manifest = ReleaseManifest.generate(environment="testing", test_count=400)
    assert manifest.deployment_environment == "testing"
    assert manifest.test_count == 400
    assert manifest.hardware_access is False
    assert manifest.network_model_download is False
    assert manifest.core_architecture_version == "V1-V9"
