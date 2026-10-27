from dataclasses import dataclass

from .geo import haversine_km, walk_minutes
from .models import PriceQuote, Store


@dataclass(frozen=True)
class Deal:
    store: Store
    quote: PriceQuote
    km: float | None
    walk_min: float | None
    trip_cents: int | None

    @property
    def effective_cents(self) -> int | None:
        return None if self.trip_cents is None else self.quote.price_cents + self.trip_cents


def rank(
    pairs: list[tuple[Store, PriceQuote]],
    lat: float,
    lon: float,
    value_of_time: float,
    round_trip: bool = False,
) -> list[Deal]:
    """Order deals by price + the cost of walking there.

    value_of_time is dollars per hour. Stores without coordinates can't be
    costed, so they go last, cheapest first, rather than being dropped.
    """
    deals = []
    for store, quote in pairs:
        if store.lat is None or store.lon is None:
            deals.append(Deal(store, quote, None, None, None))
            continue
        km = haversine_km(lat, lon, store.lat, store.lon)
        minutes = walk_minutes(km) * (2 if round_trip else 1)
        deals.append(Deal(store, quote, km, minutes, round(minutes / 60 * value_of_time * 100)))
    return sorted(deals, key=lambda d: (
        d.effective_cents is None,
        d.effective_cents if d.effective_cents is not None else d.quote.price_cents,
    ))
