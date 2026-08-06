"""Main entry point script for the Maparr CLI."""

from __future__ import annotations

import argparse

import uvicorn

from .main import create_app


def main():
    parser = argparse.ArgumentParser(description="Maparr: Self-hosted offline map manager.")
    parser.add_argument("--host", default="0.0.0.0", help="Host to run the server on.")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on.")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reloading.")
    parser.add_argument("--log-level", default="info", help="Logging level (e.g., debug, info, warning, error).")
    parser.add_argument("--data-dir", default="data", help="Directory for data storage.")
    parser.add_argument("--config-dir", default="data", help="Directory for configuration.")
    parser.add_argument("--backup-dir", default="data/backups", help="Directory for backups.")
    parser.add_argument("--tmp-dir", default="data/tmp", help="Directory for temporary files.")
    parser.add_argument("--uvicorn-log-level", default="warning", help="Logging level for Uvicorn.")
    args = parser.parse_args()

    # Environment variables take precedence, but CLI args can override.
    import os
    os.environ.setdefault("MAPARR_DATA_DIR", args.data_dir)
    os.environ.setdefault("MAPARR_CONFIG_DIR", args.config_dir)
    os.environ.setdefault("MAPARR_BACKUP_DIR", args.backup_dir)
    os.environ.setdefault("MAPARR_TMP_DIR", args.tmp_dir)
    os.environ.setdefault("MAPARR_LOG_LEVEL", args.log_level)

    uvicorn.run(create_app, host=args.host, port=args.port, reload=args.reload,
                  log_level=args.uvicorn_log_level)


if __name__ == "__main__":
    main()
