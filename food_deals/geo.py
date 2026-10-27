import json
import math
import urllib.parse
import urllib.request

EARTH_RADIUS_KM = 6371.0
# Manhattan's grid makes the walk ~1.3x the straight line.
WALK_DETOUR = 1.3
WALK_KMH = 5.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def walk_minutes(km: float) -> float:
    return km * WALK_DETOUR / WALK_KMH * 60


def google_geocode(query: str, api_key: str) -> tuple[float, float] | None:
    url = "https://maps.googleapis.com/maps/api/geocode/json?" + urllib.parse.urlencode(
        {"address": query, "key": api_key}
    )
    with urllib.request.urlopen(url, timeout=15) as resp:
        return parse_google_geocode(json.load(resp))


def parse_google_geocode(body: dict) -> tuple[float, float] | None:
    if body.get("status") == "ZERO_RESULTS":
        return None
    if body.get("status") != "OK":
        # REQUEST_DENIED / OVER_QUERY_LIMIT are configuration problems, not
        # "address not found" — fail loudly rather than leave stores unplaced.
        raise RuntimeError(f"geocoding failed: {body.get('status')} {body.get('error_message', '')}".strip())
    loc = body["results"][0]["geometry"]["location"]
    return loc["lat"], loc["lng"]
