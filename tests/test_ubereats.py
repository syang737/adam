"""Fixtures are real connector responses (2026-10-27) with image_url/actions stripped."""

import json
from datetime import datetime, timezone
from pathlib import Path

from food_deals.sources.ubereats import parse_price, parse_search

FIXTURES = Path(__file__).parent / "fixtures"
T0 = datetime(2026, 10, 27, 20, 0, tzinfo=timezone.utc)


def load(name):
    return parse_search(json.loads((FIXTURES / name).read_text()), T0)


def test_splits_chain_and_address_from_name():
    stores, _ = load("ubereats_times_square.json")
    tb = next(s for s in stores if s.source_store_id == "d48d6f92-d9dc-44b2-9fd1-2e795bd25873")
    assert (tb.chain, tb.address, tb.area) == ("Taco Bell", "1501 Broadway Suite #7", "New York, NY")


def test_name_without_address_is_its_own_chain():
    stores, _ = load("ubereats_times_square.json")
    maiz = next(s for s in stores if s.name == "Maiz")
    assert (maiz.chain, maiz.address) == ("Maiz", None)


def test_null_items_yield_store_but_no_quotes():
    stores, quotes = load("ubereats_harlem.json")
    kfc = next(s for s in stores if s.chain == "KFC")
    assert not [q for q in quotes if q.source_store_id == kfc.source_store_id]


def test_crunchwrap_prices_per_store():
    _, quotes = load("ubereats_harlem.json")
    cw = sorted(q.price_cents for q in quotes if q.item_key == "crunchwrap supreme")
    assert cw == [975, 975, 1085, 1085]
    assert all(q.channel == "delivery" for q in quotes)


def test_combo_and_variants_are_distinct_items():
    _, quotes = load("ubereats_times_square.json")
    keys = {q.item_key for q in quotes if "crunchwrap" in q.item_key}
    assert keys == {"crunchwrap supreme", "crunchwrap supreme combo", "black bean crunchwrap supreme"}


def test_parse_price():
    assert parse_price("$10.48") == 1048
    assert parse_price("$24") == 2400
    assert parse_price("") is None
    assert parse_price(None) is None
    assert parse_price("Market price") is None
