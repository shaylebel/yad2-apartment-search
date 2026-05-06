import json
import sqlite3
import logging
from pathlib import Path
from models.listing import ApartmentListing
from database.queries import build_filter_query

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    listing_id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    price INTEGER,
    rooms REAL,
    size_sqm INTEGER,
    floor INTEGER,
    total_floors INTEGER,
    city TEXT,
    neighborhood TEXT,
    street TEXT,
    address_full TEXT,
    has_elevator BOOLEAN,
    has_parking BOOLEAN,
    has_balcony BOOLEAN,
    has_ac BOOLEAN,
    is_furnished BOOLEAN,
    pets_allowed BOOLEAN,
    has_mamad BOOLEAN,
    has_bars BOOLEAN,
    thumbnail_url TEXT,
    image_urls TEXT,
    description TEXT,
    contact_name TEXT,
    date_published TEXT,
    date_updated TEXT,
    date_scraped TEXT NOT NULL,
    raw_text TEXT
);

CREATE INDEX IF NOT EXISTS idx_price ON listings(price);
CREATE INDEX IF NOT EXISTS idx_rooms ON listings(rooms);
CREATE INDEX IF NOT EXISTS idx_city ON listings(city);
CREATE INDEX IF NOT EXISTS idx_date_scraped ON listings(date_scraped);
"""


class Database:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def upsert_listing(self, listing: ApartmentListing):
        data = listing.model_dump()
        data["image_urls"] = json.dumps(data["image_urls"])
        data["date_scraped"] = str(data["date_scraped"])

        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        sql = f"INSERT OR REPLACE INTO listings ({columns}) VALUES ({placeholders})"
        self.conn.execute(sql, list(data.values()))
        self.conn.commit()

    def upsert_many(self, listings: list[ApartmentListing]):
        for listing in listings:
            data = listing.model_dump()
            data["image_urls"] = json.dumps(data["image_urls"])
            data["date_scraped"] = str(data["date_scraped"])

            columns = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            sql = f"INSERT OR REPLACE INTO listings ({columns}) VALUES ({placeholders})"
            self.conn.execute(sql, list(data.values()))
        self.conn.commit()
        logger.info(f"Upserted {len(listings)} listings")

    def query_listings(
        self,
        filters: dict,
        sort_by: str = "date_scraped",
        sort_order: str = "DESC",
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        allowed_sort = {
            "price", "rooms", "size_sqm", "floor", "date_scraped", "address_full"
        }
        if sort_by not in allowed_sort:
            sort_by = "date_scraped"
        if sort_order not in ("ASC", "DESC"):
            sort_order = "DESC"

        where_clause, params = build_filter_query(filters)
        sql = (
            f"SELECT * FROM listings WHERE {where_clause} "
            f"ORDER BY {sort_by} {sort_order} LIMIT ? OFFSET ?"
        )
        params.extend([limit, offset])

        rows = self.conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def count_listings(self, filters: dict) -> int:
        where_clause, params = build_filter_query(filters)
        sql = f"SELECT COUNT(*) FROM listings WHERE {where_clause}"
        return self.conn.execute(sql, params).fetchone()[0]

    def clear_all(self):
        self.conn.execute("DELETE FROM listings")
        self.conn.commit()

    def close(self):
        self.conn.close()
