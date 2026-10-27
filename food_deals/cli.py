import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import db
from .catalog import chain_key, item_key
from .geo import google_geocode
from .scoring import rank
from .sources import ubereats

DEFAULT_DB = "food_deals.sqlite"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="food-deals")
    p.add_argument("--db", default=os.environ.get("FOOD_DEALS_DB", DEFAULT_DB))
    sub = p.add_subparsers(dest="cmd", required=True)

    ing = sub.add_parser("ingest", help="load saved Uber Eats search responses")
    ing.add_argument("files", nargs="+", type=Path)
    ing.add_argument("--fetched-at", help="ISO time the searches ran (default: file mtime)")

    geo = sub.add_parser("geocode", help="place stores without coordinates (needs GOOGLE_MAPS_API_KEY)")
    geo.add_argument("--dry-run", action="store_true", help="list the queries without calling Google")

    loc = sub.add_parser("locate", help="set a store's coordinates by hand")
    loc.add_argument("store_id")
    loc.add_argument("lat", type=float)
    loc.add_argument("lon", type=float)
    loc.add_argument("--source", default=ubereats.SOURCE)

    rk = sub.add_parser("rank", help="nearby stores for an item, cheapest once the walk is counted")
    rk.add_argument("item")
    rk.add_argument("--lat", type=float, required=True)
    rk.add_argument("--lon", type=float, required=True)
    rk.add_argument("--chain")
    rk.add_argument("--vot", type=float, default=20.0, help="value of your time, $/hr (default 20)")
    rk.add_argument("--round-trip", action="store_true", help="count the walk back too")
    rk.add_argument("--channel", default="delivery")

    args = p.parse_args(argv)
    conn = db.connect(args.db)
    return {"ingest": _ingest, "geocode": _geocode, "locate": _locate, "rank": _rank}[args.cmd](conn, args)


def _ingest(conn, args) -> int:
    for path in args.files:
        fetched_at = (
            datetime.fromisoformat(args.fetched_at) if args.fetched_at
            else datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        )
        stores, quotes = ubereats.parse_search(json.loads(path.read_text()), fetched_at)
        db.save(conn, stores, quotes)
        print(f"{path}: {len(stores)} stores, {len(quotes)} prices")
    return 0


def _geocode(conn, args) -> int:
    stores = [s for s in db.unplaced(conn) if s.address]
    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not args.dry_run and not key:
        print("GOOGLE_MAPS_API_KEY is not set (or use --dry-run, or `locate` by hand)", file=sys.stderr)
        return 2
    for s in stores:
        query = ", ".join(x for x in (s.address, s.area) if x)
        if args.dry_run:
            print(f"{s.source_store_id}  {query}")
            continue
        found = google_geocode(query, key)
        if found is None:
            print(f"not found: {query}", file=sys.stderr)
            continue
        db.set_location(conn, s.source, s.source_store_id, *found)
        print(f"{s.name}: {found[0]:.5f}, {found[1]:.5f}")
    return 0


def _locate(conn, args) -> int:
    db.set_location(conn, args.source, args.store_id, args.lat, args.lon)
    return 0


def _rank(conn, args) -> int:
    pairs = db.latest_quotes(
        conn, item_key(args.item), args.chain and chain_key(args.chain), args.channel
    )
    if not pairs:
        print(f"no {args.channel} prices for {args.item!r}", file=sys.stderr)
        return 1
    for d in rank(pairs, args.lat, args.lon, args.vot, args.round_trip):
        price = f"${d.quote.price_cents / 100:.2f}"
        if d.effective_cents is None:
            print(f"   {price:>7}  {'(no location)':>27}  {d.store.name}")
        else:
            print(
                f"{'':>2} {price:>7}  + ${d.trip_cents / 100:.2f} walk ({d.walk_min:3.0f} min)"
                f" = ${d.effective_cents / 100:.2f}  {d.store.name}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
