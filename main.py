"""Backward-compatible source-tree launcher for the packaged MCP server."""

from excalidraw_mcp.server import create_server, mcp, run

__all__ = ["create_server", "mcp", "run"]


if __name__ == "__main__":
    run()
