import sqlite3
from datetime import datetime
from pathlib import Path

from .catalog import chain_key
from .models import PriceQuote, Store

SCHEMA = """
create table if not exists stores (
    source text not null,
    source_store_id text not null,
    chain text not null,
    chain_key text not null,
    name text not null,
    address text,
    area text,
    lat real,
    lon real,
    primary key (source, source_store_id)
);
create table if not exists quotes (
    source text not null,
    source_store_id text not null,
    item_key text not null,
    item_name text not null,
    price_cents integer not null,
    channel text not null,
    fetched_at text not null,
    primary key (source, source_store_id, item_key, channel, fetched_at)
);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def save(conn: sqlite3.Connection, stores: list[Store], quotes: list[PriceQuote]) -> None:
    with conn:
        for s in stores:
            # A re-ingest must not wipe coordinates geocoded earlier.
            conn.execute(
                """insert into stores values (?,?,?,?,?,?,?,?,?)
                   on conflict (source, source_store_id) do update set
                     chain=excluded.chain, chain_key=excluded.chain_key, name=excluded.name,
                     address=excluded.address, area=coalesce(stores.area, excluded.area)""",
                (s.source, s.source_store_id, s.chain, chain_key(s.chain), s.name,
                 s.address, s.area, s.lat, s.lon),
            )
        conn.executemany(
            "insert or replace into quotes values (?,?,?,?,?,?,?)",
            [(q.source, q.source_store_id, q.item_key, q.item_name, q.price_cents,
              q.channel, q.fetched_at.isoformat()) for q in quotes],
        )


def set_location(conn: sqlite3.Connection, source: str, store_id: str, lat: float, lon: float) -> None:
    with conn:
        conn.execute(
            "update stores set lat=?, lon=? where source=? and source_store_id=?",
            (lat, lon, source, store_id),
        )


def unplaced(conn: sqlite3.Connection) -> list[Store]:
    rows = conn.execute(
        "select source, source_store_id, chain, name, address, area, lat, lon"
        " from stores where lat is null"
    ).fetchall()
    return [Store(*r) for r in rows]


def latest_quotes(
    conn: sqlite3.Connection, item: str, chain: str | None, channel: str
) -> list[tuple[Store, PriceQuote]]:
    """The most recent quote for `item` at each store."""
    rows = conn.execute(
        """select s.source, s.source_store_id, s.chain, s.name, s.address, s.area, s.lat, s.lon,
                  q.item_key, q.item_name, q.price_cents, q.channel, q.fetched_at
           from quotes q
           join stores s using (source, source_store_id)
           where q.item_key = ? and q.channel = ? and (? is null or s.chain_key = ?)
             and q.fetched_at = (
               select max(fetched_at) from quotes q2
               where q2.source = q.source and q2.source_store_id = q.source_store_id
                 and q2.item_key = q.item_key and q2.channel = q.channel)""",
        (item, channel, chain, chain),
    ).fetchall()
    return [
        (Store(*r[:8]), PriceQuote(r[0], r[1], r[8], r[9], r[10], r[11], datetime.fromisoformat(r[12])))
        for r in rows
    ]
