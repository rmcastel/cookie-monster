CREATE TABLE IF NOT EXISTS stores (
    slug        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    city        TEXT,
    state       TEXT,
    discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS menu_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    week_of     DATE    NOT NULL,
    scraped_at  DATETIME NOT NULL,
    store_slug  TEXT    NOT NULL REFERENCES stores(slug),
    cookie_id   TEXT    NOT NULL,
    cookie_name TEXT    NOT NULL,
    flavor_type TEXT    NOT NULL CHECK(flavor_type IN ('weekly', 'classic')),
    secret_menu TEXT,
    cal_count   INTEGER NOT NULL,
    UNIQUE(week_of, store_slug, cookie_id)
);

CREATE INDEX IF NOT EXISTS idx_menu_week    ON menu_items(week_of);
CREATE INDEX IF NOT EXISTS idx_menu_store   ON menu_items(store_slug);
CREATE INDEX IF NOT EXISTS idx_menu_cookie  ON menu_items(cookie_name);
