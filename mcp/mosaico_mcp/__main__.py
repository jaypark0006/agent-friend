"""Allow running the MCP server via `python3 -m mosaico_mcp`."""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
