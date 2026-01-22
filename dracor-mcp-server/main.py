#!/usr/bin/env python3
"""
DraCor MCP Server - Entry point with transport selection.

This module handles transport selection (stdio vs HTTP) based on environment
variables and configures the appropriate server mode.

Environment Variables:
    TRANSPORT: Transport mode - "stdio" (default) or "streamable-http"
    HOST: HTTP server bind address (default: "0.0.0.0")
    PORT: HTTP server port (default: 8000, Railway sets automatically)
    LOG_LEVEL: Uvicorn log level (default: "info")
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_http_app():
    """Create the HTTP app for MCP streaming.

    The health check is defined in server.py using @mcp.custom_route.
    We just need to return the streamable HTTP app.
    """
    from server import mcp
    return mcp.streamable_http_app()


def run_stdio():
    """Run the MCP server in stdio mode (for Claude Desktop)."""
    from server import mcp
    logger.info("Starting DraCor MCP server in stdio mode...")
    mcp.run()


def run_http():
    """Run the MCP server in HTTP mode (for Railway deployment)."""
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))
    log_level = os.environ.get("LOG_LEVEL", "info").lower()

    logger.info(f"Starting DraCor MCP server in HTTP mode on {host}:{port}...")

    app = create_http_app()

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
    )


def main():
    """Main entry point with transport selection."""
    transport = os.environ.get("TRANSPORT", "stdio").lower()

    if transport == "stdio":
        run_stdio()
    elif transport == "streamable-http":
        run_http()
    else:
        logger.error(f"Unknown transport: {transport}. Use 'stdio' or 'streamable-http'.")
        raise ValueError(f"Unknown transport: {transport}")


if __name__ == "__main__":
    main()
