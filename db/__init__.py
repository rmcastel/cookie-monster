import aiosqlite
import pathlib
from datetime import date, datetime
from typing import Any

DB_PATH = pathlib.Path(__file__).parent.parent / "cookie_monster.db"
SCHEMA_PATH = pathlib.Path(__file__).parent / "schema.sql"


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute("PRAGMA journal_mode = WAL")
    return db


async def init_db() -> None:
    schema = SCHEMA_PATH.read_text()
    db = await get_db()
    try:
        await db.executescript(schema)
        await db.commit()
    finally:
        await db.close()


async def upsert_store(db: aiosqlite.Connection, slug: str, name: str, city: str | None, state: str | None) -> None:
    await db.execute(
        """
        INSERT INTO stores (slug, name, city, state)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
            name  = excluded.name,
            city  = excluded.city,
            state = excluded.state
        """,
        (slug, name, city, state),
    )


async def insert_menu_item(
    db: aiosqlite.Connection,
    week_of: date,
    store_slug: str,
    cookie_id: str,
    cookie_name: str,
    flavor_type: str,
    secret_menu: str,
    cal_count: int
) -> None:
    await db.execute(
        """
        INSERT OR IGNORE INTO menu_items (week_of, scraped_at, store_slug, cookie_id, cookie_name, flavor_type, secret_menu, cal_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (week_of.isoformat(), datetime.utcnow().isoformat(), store_slug, cookie_id, cookie_name, flavor_type, secret_menu, cal_count),
    )
