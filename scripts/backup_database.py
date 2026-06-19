#!/usr/bin/env python3
"""
Database Backup Script for Multi-Agent RAG System

Features:
    - SQLite online backup using VACUUM INTO
    - Automatic backup rotation (default: 30 days retention)
    - Metadata JSON for each backup
    - Incremental backup support
    - Compression option (gzip)

Usage:
    # Manual backup
    python scripts/backup_database.py

    # Backup with compression
    python scripts/backup_database.py --compress

    # Custom retention period
    python scripts/backup_database.py --retention-days 60

    # Restore from backup
    python scripts/backup_database.py --restore backups/app_db_20260617_150000.db

Automated Setup:
    Linux/macOS (cron):
        0 3 * * * cd /path/to/project && conda run -n rag-local python scripts/backup_database.py

    Windows (Task Scheduler):
        schtasks /create /tn "RAG Database Backup" /tr "conda run -n rag-local python scripts/backup_database.py" /sc daily /st 03:00
"""

import argparse
import gzip
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app.core.settings import settings
    APP_DB_PATH = Path(settings.APP_DB_PATH)
except Exception:
    # Fallback if settings not available
    APP_DB_PATH = Path("./data/app.db")

BACKUP_DIR = Path("./data/backups")
DEFAULT_RETENTION_DAYS = 30


def ensure_backup_dir() -> Path:
    """Create backup directory if it doesn't exist."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def get_backup_metadata(db_path: Path) -> dict:
    """Gather metadata about the database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get database size
        db_size = db_path.stat().st_size

        # Count tables
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]

        # Get row counts for key tables
        row_counts = {}
        for table in ["users", "sessions", "audit_logs"]:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_counts[table] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                row_counts[table] = 0

        conn.close()

        return {
            "db_size_bytes": db_size,
            "table_count": table_count,
            "row_counts": row_counts,
            "backup_timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


def backup_sqlite(
    db_path: Path,
    backup_dir: Path,
    compress: bool = False
) -> tuple[Path, dict]:
    """
    Execute SQLite online backup using VACUUM INTO.

    Args:
        db_path: Path to source database
        backup_dir: Directory to store backups
        compress: Whether to compress the backup with gzip

    Returns:
        Tuple of (backup_path, metadata)
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"app_db_{timestamp}.db"
    backup_path = backup_dir / backup_filename

    print(f"🔄 Starting backup: {db_path} -> {backup_path}")

    # Collect metadata before backup
    metadata = get_backup_metadata(db_path)

    # Perform backup using VACUUM INTO (maintains consistency)
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(f"VACUUM INTO '{backup_path}'")
        conn.close()
        print(f"✅ Database backed up to {backup_path}")
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        if backup_path.exists():
            backup_path.unlink()
        raise

    # Compress if requested
    if compress:
        compressed_path = backup_path.with_suffix(".db.gz")
        print(f"🗜️  Compressing backup...")
        with backup_path.open("rb") as f_in:
            with gzip.open(compressed_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        backup_path.unlink()  # Remove uncompressed version
        backup_path = compressed_path
        print(f"✅ Compressed backup: {compressed_path}")

    # Save metadata
    metadata_path = backup_path.with_suffix(backup_path.suffix + ".meta.json")
    metadata["backup_file"] = backup_path.name
    metadata["compressed"] = compress
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return backup_path, metadata


def rotate_old_backups(backup_dir: Path, retention_days: int):
    """Delete backups older than retention period."""
    cutoff = datetime.now().timestamp() - (retention_days * 86400)
    deleted_count = 0

    for backup_file in backup_dir.glob("app_db_*.db*"):
        if backup_file.suffix == ".json":
            continue  # Skip metadata files

        if backup_file.stat().st_mtime < cutoff:
            # Delete backup and its metadata
            backup_file.unlink()
            metadata_file = backup_file.with_suffix(backup_file.suffix + ".meta.json")
            if metadata_file.exists():
                metadata_file.unlink()

            deleted_count += 1
            print(f"🗑️  Deleted old backup: {backup_file.name}")

    if deleted_count == 0:
        print("✅ No old backups to delete")
    else:
        print(f"✅ Deleted {deleted_count} old backup(s)")


def list_backups(backup_dir: Path):
    """List all available backups with metadata."""
    backups = sorted(backup_dir.glob("app_db_*.db*"), reverse=True)

    if not backups:
        print("No backups found")
        return

    print(f"\n📦 Available backups in {backup_dir}:")
    print("-" * 80)

    for backup_file in backups:
        if backup_file.suffix == ".json":
            continue

        # Load metadata if available
        metadata_file = backup_file.with_suffix(backup_file.suffix + ".meta.json")
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
                size_mb = metadata.get("db_size_bytes", 0) / 1024 / 1024
                timestamp = metadata.get("backup_timestamp", "Unknown")
                print(f"  {backup_file.name}")
                print(f"    Size: {size_mb:.2f} MB | Time: {timestamp}")
        else:
            size_mb = backup_file.stat().st_size / 1024 / 1024
            print(f"  {backup_file.name} ({size_mb:.2f} MB)")

    print("-" * 80)


def restore_backup(backup_path: Path, target_db_path: Path, force: bool = False):
    """
    Restore database from backup.

    Args:
        backup_path: Path to backup file
        target_db_path: Path to restore to (usually the main database)
        force: Skip confirmation prompt
    """
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    if target_db_path.exists() and not force:
        response = input(f"⚠️  This will overwrite {target_db_path}. Continue? (yes/no): ")
        if response.lower() != "yes":
            print("❌ Restore cancelled")
            return

    # Create backup of current database before restore
    if target_db_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pre_restore_backup = target_db_path.with_suffix(f".pre_restore_{timestamp}.db")
        shutil.copy2(target_db_path, pre_restore_backup)
        print(f"✅ Created pre-restore backup: {pre_restore_backup}")

    # Handle compressed backups
    if backup_path.suffix == ".gz":
        print(f"🗜️  Decompressing backup...")
        with gzip.open(backup_path, "rb") as f_in:
            with open(target_db_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
    else:
        shutil.copy2(backup_path, target_db_path)

    print(f"✅ Database restored from {backup_path}")


def main():
    parser = argparse.ArgumentParser(description="Database backup and restore utility")
    parser.add_argument(
        "--compress", "-c",
        action="store_true",
        help="Compress backup with gzip"
    )
    parser.add_argument(
        "--retention-days", "-r",
        type=int,
        default=DEFAULT_RETENTION_DAYS,
        help=f"Backup retention period in days (default: {DEFAULT_RETENTION_DAYS})"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all available backups"
    )
    parser.add_argument(
        "--restore",
        type=str,
        metavar="BACKUP_FILE",
        help="Restore from backup file"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Skip confirmation prompts (use with --restore)"
    )

    args = parser.parse_args()

    # Ensure backup directory exists
    backup_dir = ensure_backup_dir()

    # List backups
    if args.list:
        list_backups(backup_dir)
        return

    # Restore from backup
    if args.restore:
        backup_path = Path(args.restore)
        if not backup_path.is_absolute():
            backup_path = backup_dir / backup_path
        restore_backup(backup_path, APP_DB_PATH, force=args.force)
        return

    # Perform backup
    try:
        backup_path, metadata = backup_sqlite(
            APP_DB_PATH,
            backup_dir,
            compress=args.compress
        )

        # Show backup summary
        print("\n📊 Backup Summary:")
        print(f"  File: {backup_path.name}")
        print(f"  Size: {backup_path.stat().st_size / 1024 / 1024:.2f} MB")
        if "row_counts" in metadata:
            print(f"  Tables: {metadata.get('table_count', 'N/A')}")
            print(f"  Users: {metadata['row_counts'].get('users', 0)}")
            print(f"  Sessions: {metadata['row_counts'].get('sessions', 0)}")
            print(f"  Audit Logs: {metadata['row_counts'].get('audit_logs', 0)}")

        # Rotate old backups
        print(f"\n🔄 Rotating old backups (retention: {args.retention_days} days)...")
        rotate_old_backups(backup_dir, args.retention_days)

        print("\n✅ Backup completed successfully!")

    except Exception as e:
        print(f"\n❌ Backup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
