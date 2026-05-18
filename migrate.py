"""MongoDB index bootstrap for OutfitDuel.

MongoDB is schemaless so we don't `CREATE TABLE`. Instead we create the indexes
that the app actually relies on. Run once per deploy:

    python3 migrate.py

Safe to re-run — indexes are idempotent.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING, MongoClient

ROOT = Path(__file__).parent
load_dotenv(ROOT / "backend" / ".env")
load_dotenv(ROOT / ".env")

mongo_url = os.environ.get("MONGO_URL")
db_name = os.environ.get("DB_NAME")

if not mongo_url or not db_name:
    print("ERROR: MONGO_URL and DB_NAME must be set in backend/.env or .env")
    sys.exit(1)


def main() -> None:
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=10_000)
    # Force connection error early
    client.admin.command("ping")
    db = client[db_name]

    print(f"Connected to {db_name} on {mongo_url}")

    # duels collection
    db.duels.create_index([("id", ASCENDING)], unique=True, name="duels_id_unique")
    db.duels.create_index([("created_at", DESCENDING)], name="duels_created_at")
    db.duels.create_index([("expires_at", ASCENDING)], name="duels_expires_at")
    db.duels.create_index([("is_hidden", ASCENDING)], name="duels_is_hidden")
    print("✓ duels indexes")

    # votes collection
    db.votes.create_index(
        [("duel_id", ASCENDING), ("voter_hash", ASCENDING)],
        name="votes_dedup_voter",
    )
    db.votes.create_index(
        [("duel_id", ASCENDING), ("cookie_id", ASCENDING)],
        name="votes_dedup_cookie",
    )
    print("✓ votes indexes")

    # reports collection
    db.reports.create_index(
        [("duel_id", ASCENDING), ("ip_hash", ASCENDING)],
        unique=True,
        name="reports_dedup",
    )
    db.reports.create_index([("created_at", DESCENDING)], name="reports_created_at")
    print("✓ reports indexes")

    # stats singleton
    db.stats.create_index([("_id", ASCENDING)], name="stats_pk")
    print("✓ stats indexes")

    print("Migration complete.")


if __name__ == "__main__":
    main()
