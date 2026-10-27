from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Store:
    source: str
    source_store_id: str
    chain: str
    name: str
    # Street address as the source gives it, and the area it was found in.
    # Together they make a geocodable query: "1501 Broadway, New York, NY".
    address: str | None
    area: str | None
    lat: float | None = None
    lon: float | None = None


@dataclass(frozen=True)
class PriceQuote:
    source: str
    source_store_id: str
    item_key: str
    item_name: str
    price_cents: int
    # "delivery" prices carry the app's markup; "pickup" are in-store.
    # Never compare across channels as if they were the same price.
    channel: str
    fetched_at: datetime
