"""Parse responses from the Uber Eats connector's `search` tool.

The connector is reachable through Claude, not from this process, so ingest
works on saved responses: a Claude session (or scheduled task) runs the
search and drops the JSON into a folder, and `food-deals ingest` reads it.

A query naming chain + item ("Taco Bell Crunchwrap Supreme") returns each
nearby store of the chain with item-level prices. A bare chain name returns
stores with `items: null`. Prices are delivery-menu prices, so they include
the app's markup but not its fees.
"""

import re
from datetime import datetime

from ..catalog import item_key
from ..models import PriceQuote, Store

SOURCE = "ubereats"

# "Taco Bell (1501 Broadway Suite #7)" -> chain, address
_NAME_WITH_ADDRESS = re.compile(r"^(?P<chain>.+?)\s*\((?P<address>[^()]+)\)\s*$")
_ZIP_AND_COUNTRY = re.compile(r"\s+\d{5}(-\d{4})?\b|,\s*USA$")


def parse_search(response: dict, fetched_at: datetime) -> tuple[list[Store], list[PriceQuote]]:
    area = _area(response.get("metadata", {}).get("full_address"))
    stores, quotes = [], []
    for merchant in response.get("merchants") or []:
        store_id = merchant["store_id"]
        chain, address = _split_name(merchant["name"])
        stores.append(Store(SOURCE, store_id, chain, merchant["name"], address, area))
        for item in merchant.get("items") or []:
            cents = parse_price(item.get("price"))
            if cents is None:
                continue
            quotes.append(PriceQuote(
                SOURCE, store_id, item_key(item["name"]), item["name"],
                cents, "delivery", fetched_at,
            ))
    return stores, quotes


def parse_price(text: str | None) -> int | None:
    """"$10.48" -> 1048. Blank or unparseable prices are skipped, not zeroed."""
    if not text:
        return None
    m = re.fullmatch(r"\$(\d+)(?:\.(\d{2}))?", text.strip())
    if not m:
        return None
    return int(m[1]) * 100 + int(m[2] or 0)


def _split_name(name: str) -> tuple[str, str | None]:
    m = _NAME_WITH_ADDRESS.match(name)
    if not m:
        return name.strip(), None
    return m["chain"], m["address"].strip()


def _area(full_address: str | None) -> str | None:
    """"W 45th St & 7th Ave, New York, NY 10036, USA" -> "New York, NY".

    The zip is dropped because it is the searcher's, not the store's.
    """
    if not full_address or "," not in full_address:
        return None
    return _ZIP_AND_COUNTRY.sub("", full_address.split(",", 1)[1]).strip(" ,")
