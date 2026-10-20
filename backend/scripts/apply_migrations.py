"""Apply supabase/migrations/*.sql to the database in DATABASE_URL (from backend/.env).

Usage (from backend/):  python -m scripts.apply_migrations

Each file runs in its own transaction and is recorded in interviewiq_meta.schema_migrations
(a private schema, not exposed by Supabase's Data API), so re-running is safe: files that
were already applied are skipped.
"""

import asyncio
import sys
from pathlib import Path

import asyncpg

from app.core.config import get_settings

MIGRATIONS = Path(__file__).resolve().parents[2] / "supabase" / "migrations"


def plain_dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def main() -> int:
    settings = get_settings()
    if settings.is_sqlite:
        print("DATABASE_URL points at SQLite. Set it to your Supabase Postgres URL first.")
        return 1
    conn = await asyncpg.connect(plain_dsn(settings.database_url), statement_cache_size=0)
    try:
        await conn.execute(
            "create schema if not exists interviewiq_meta;"
            "revoke all on schema interviewiq_meta from public;"
            "create table if not exists interviewiq_meta.schema_migrations ("
            " filename text primary key, applied_at timestamptz not null default now())"
        )
        rows = await conn.fetch("select filename from interviewiq_meta.schema_migrations")
        done = {r["filename"] for r in rows}
        files = sorted(MIGRATIONS.glob("*.sql"))
        for f in files:
            if f.name in done:
                print(f"skip     {f.name} (already applied)")
                continue
            async with conn.transaction():
                await conn.execute(f.read_text(encoding="utf-8"))
                await conn.execute(
                    "insert into interviewiq_meta.schema_migrations (filename) values ($1)", f.name
                )
            print(f"applied  {f.name}")
        print("Migrations up to date.")
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
