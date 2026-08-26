"""Backward-compatible entry point forwarding to canonical SkyVanta CLI."""

import sys
from skyvanta.cli import main

if __name__ == "__main__":
    main()