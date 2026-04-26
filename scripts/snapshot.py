#!/usr/bin/env python3
"""Snapshot Wispr Flow's live SQLite to a read-only working copy.

Wispr Flow opens flow.sqlite in WAL mode while running. Direct reads against
the live file can race with the app. This helper makes a safe snapshot using
SQLite's online backup API, which respects WAL semantics.

Usage:
    python scripts/snapshot.py

Reads SOURCE from config.py (default macOS path) and writes to data/snapshot.sqlite.
"""

import shutil
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402


def main():
    src = config.get_flow_sqlite_path()
    dst = config.get_snapshot_path()

    if not src.exists():
        print(f"ERROR: Wispr Flow SQLite not found at: {src}")
        print("Edit config.py FLOW_SQLITE_PATH to point at your install.")
        sys.exit(2)

    dst.parent.mkdir(parents=True, exist_ok=True)
    print(f"Source : {src}  ({src.stat().st_size / 1e9:.2f} GB)")
    print(f"Target : {dst}")

    # Use SQLite's backup API. It is safe even if Flow is running.
    src_uri = f"file:{src}?mode=ro"
    src_conn = sqlite3.connect(src_uri, uri=True)
    if dst.exists():
        dst.unlink()
    dst_conn = sqlite3.connect(str(dst))
    with dst_conn:
        src_conn.backup(dst_conn, pages=2000, progress=lambda r, p, t: print(f"  copied {t - r} / {t} pages", end="\r"))
    print()
    src_conn.close()
    dst_conn.close()
    print(f"Snapshot ready: {dst}  ({dst.stat().st_size / 1e9:.2f} GB)")


if __name__ == "__main__":
    main()
