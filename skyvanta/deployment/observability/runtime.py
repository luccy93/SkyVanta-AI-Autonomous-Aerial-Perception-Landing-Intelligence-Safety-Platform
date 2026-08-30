"""System runtime resource inspection, version metadata discovery, and threshold warning monitor."""

import os
import platform
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

try:
    import importlib.metadata as importlib_metadata
    __version__ = importlib_metadata.version("skyvanta")
except Exception:
    __version__ = "0.1.0"


class SystemResourceMonitor:
    """Monitors process resource utilization, version metadata, and warning thresholds."""

    def __init__(self):
        self._start_time = time.time()
        self._cached_git_commit: Optional[str] = None
        self._cached_build_timestamp: Optional[str] = None
        self._process = None
        if _HAS_PSUTIL:
            try:
                self._process = psutil.Process(os.getpid())
                # Initial call to prime cpu_percent
                self._process.cpu_percent(interval=None)
            except Exception:
                self._process = None

    @property
    def uptime_sec(self) -> float:
        """Returns elapsed process wall-clock uptime in seconds."""
        return float(time.time() - self._start_time)

    def get_git_commit(self) -> str:
        """Retrieves Git commit hash safely without subprocess or leaking filesystem paths."""
        if self._cached_git_commit is not None:
            return self._cached_git_commit

        # 1. Check standard deployment environment variables
        commit = (
            os.getenv("GIT_COMMIT")
            or os.getenv("RENDER_GIT_COMMIT")
            or os.getenv("GITHUB_SHA")
            or os.getenv("SOURCE_VERSION")
        )
        if commit and commit.strip():
            self._cached_git_commit = commit.strip()[:40]
            return self._cached_git_commit

        # 2. Pure Python .git reader (instantaneous, no subprocess overhead)
        try:
            head_file = os.path.join(".git", "HEAD")
            if os.path.isfile(head_file):
                with open(head_file, "r", encoding="utf-8") as f:
                    head_content = f.read().strip()
                if head_content.startswith("ref:"):
                    ref_relative = head_content[4:].strip()
                    ref_file = os.path.join(".git", ref_relative.replace("/", os.sep))
                    if os.path.isfile(ref_file):
                        with open(ref_file, "r", encoding="utf-8") as f:
                            self._cached_git_commit = f.read().strip()[:40]
                            return self._cached_git_commit
                    # Check packed-refs if branch is packed
                    packed_file = os.path.join(".git", "packed-refs")
                    if os.path.isfile(packed_file):
                        with open(packed_file, "r", encoding="utf-8") as f:
                            for line in f:
                                if ref_relative in line and not line.startswith("#"):
                                    self._cached_git_commit = line.split()[0].strip()[:40]
                                    return self._cached_git_commit
                elif len(head_content) >= 7:
                    self._cached_git_commit = head_content[:40]
                    return self._cached_git_commit
        except Exception:
            pass

        self._cached_git_commit = "unknown"
        return self._cached_git_commit

    def get_build_timestamp(self) -> str:
        """Retrieves container or package build timestamp."""
        if self._cached_build_timestamp is not None:
            return self._cached_build_timestamp

        ts = os.getenv("BUILD_TIMESTAMP") or os.getenv("RENDER_DEPLOY_TIMESTAMP")
        if ts and ts.strip():
            self._cached_build_timestamp = ts.strip()
            return self._cached_build_timestamp

        self._cached_build_timestamp = "2026-08-30T00:00:00Z"
        return self._cached_build_timestamp

    def get_resource_usage(self) -> Dict[str, Any]:
        """Collects current process CPU, memory, and runtime metrics."""
        cpu_percent = 0.0
        memory_rss_bytes = 0
        memory_rss_mb = 0.0

        if self._process is not None:
            try:
                cpu_percent = float(self._process.cpu_percent(interval=None))
                mem_info = self._process.memory_info()
                memory_rss_bytes = int(mem_info.rss)
                memory_rss_mb = round(float(memory_rss_bytes / (1024 * 1024)), 2)
            except Exception:
                pass
        elif _HAS_PSUTIL:
            try:
                proc = psutil.Process(os.getpid())
                cpu_percent = float(proc.cpu_percent(interval=None))
                memory_rss_bytes = int(proc.memory_info().rss)
                memory_rss_mb = round(float(memory_rss_bytes / (1024 * 1024)), 2)
            except Exception:
                pass

        return {
            "uptime_sec": round(self.uptime_sec, 2),
            "cpu_percent": round(cpu_percent, 1),
            "memory_rss_mb": memory_rss_mb,
            "memory_rss_bytes": memory_rss_bytes,
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "os_platform": platform.system().lower(),
            "application_version": __version__,
            "api_version": "v1",
            "git_commit": self.get_git_commit(),
            "build_timestamp": self.get_build_timestamp(),
        }

    def evaluate_warnings(
        self,
        cpu_threshold_pct: float = 85.0,
        memory_threshold_mb: float = 512.0,
        max_ws_clients: int = 50,
        active_ws_clients: int = 0,
        ws_warning_pct: float = 80.0,
    ) -> List[str]:
        """Evaluates operational thresholds and returns any active warning messages.

        Note: Operational warnings are diagnostic only and do NOT alter robotics safety logic.
        """
        warnings = []
        usage = self.get_resource_usage()

        if usage["cpu_percent"] >= cpu_threshold_pct and cpu_threshold_pct > 0:
            warnings.append(
                f"CPU usage ({usage['cpu_percent']}%) exceeds threshold ({cpu_threshold_pct}%)"
            )

        if usage["memory_rss_mb"] >= memory_threshold_mb and memory_threshold_mb > 0:
            warnings.append(
                f"Memory RSS ({usage['memory_rss_mb']} MB) exceeds threshold ({memory_threshold_mb} MB)"
            )

        if max_ws_clients > 0:
            ws_pct = (active_ws_clients / max_ws_clients) * 100.0
            if ws_pct >= ws_warning_pct:
                warnings.append(
                    f"Active WebSocket connections ({active_ws_clients}/{max_ws_clients}, {round(ws_pct, 1)}%) "
                    f"exceeds threshold ({ws_warning_pct}%)"
                )

        return warnings


# Global singleton instance
system_resource_monitor = SystemResourceMonitor()
