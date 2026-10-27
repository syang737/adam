from datetime import datetime, timezone

import pytest

from food_deals.geo import haversine_km, parse_google_geocode, walk_minutes
from food_deals.models import PriceQuote, Store
from food_deals.scoring import rank

T0 = datetime(2026, 10, 27, tzinfo=timezone.utc)
HERE = (40.0, -74.0)


def pair(store_id, cents, lat=None, lon=None):
    store = Store("test", store_id, "Chain", store_id, None, None, lat, lon)
    return store, PriceQuote("test", store_id, "item", "Item", cents, "delivery", T0)


def test_haversine_one_degree_latitude():
    assert haversine_km(40, -74, 41, -74) == pytest.approx(111.2, abs=0.1)


def test_cheap_far_store_loses_when_time_is_valuable():
    near = pair("near", 1100, 40.0, -74.0)        # here
    far = pair("far", 975, 40.0 + 2 / 111.2, -74.0)  # ~2 km north
    walk = walk_minutes(2.0)  # ~31 min
    assert [d.store.source_store_id for d in rank([near, far], *HERE, value_of_time=0)] == ["far", "near"]
    assert [d.store.source_store_id for d in rank([near, far], *HERE, value_of_time=20)] == ["near", "far"]
    assert rank([far], *HERE, value_of_time=20)[0].walk_min == pytest.approx(walk, rel=0.01)


def test_round_trip_doubles_the_walk():
    far = pair("far", 975, 40.01, -74.0)
    one = rank([far], *HERE, value_of_time=20)[0]
    both = rank([far], *HERE, value_of_time=20, round_trip=True)[0]
    assert both.walk_min == pytest.approx(2 * one.walk_min)


def test_unplaced_stores_go_last_cheapest_first():
    deals = rank([pair("u2", 900), pair("placed", 1500, *HERE), pair("u1", 800)], *HERE, value_of_time=20)
    assert [d.store.source_store_id for d in deals] == ["placed", "u1", "u2"]
    assert deals[1].effective_cents is None


def test_google_geocode_statuses():
    ok = {"status": "OK", "results": [{"geometry": {"location": {"lat": 40.7, "lng": -73.9}}}]}
    assert parse_google_geocode(ok) == (40.7, -73.9)
    assert parse_google_geocode({"status": "ZERO_RESULTS", "results": []}) is None
    with pytest.raises(RuntimeError, match="REQUEST_DENIED"):
        parse_google_geocode({"status": "REQUEST_DENIED", "error_message": "bad key"})
