"""Unit tests for H3-06: Root entrypoint forwarder verification."""

import inspect
import sys
import pytest
import main as root_main
from skyvanta.cli import main as cli_main


def test_root_main_is_minimal_forwarder():
    """Verifies root main.py is a clean forwarder to skyvanta.cli.main without subprocesses."""
    # Check that main function in root_main matches cli_main
    assert root_main.main is cli_main

    # Inspect source code of root main.py
    source = inspect.getsource(root_main)
    assert "pip" not in source
    assert "install" not in source
    assert "subprocess" not in source
    assert "importlib" not in source
    assert "--break-system-packages" not in source
