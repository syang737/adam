# food_deals

Find the cheapest nearby location for a fast-food item once the walk is
counted. Chains let franchisees set prices per store, so the same item can
cost noticeably more one location over.

Personal tool. Price data stays local (`*.sqlite` is gitignored) and is not
for redistribution.

## Spike findings (2026-10-27)

**The Uber Eats connector returns item-level prices per store.** Searching
"Taco Bell Crunchwrap Supreme" from an address returns each nearby Taco Bell
with the prices of the matching items. A bare "Taco Bell" search returns
stores with no items, so the query has to name the item.

Crunchwrap Supreme, Uber Eats delivery menu:

| Store | Area | Price |
|---|---|---|
| 976 6th Avenue | Herald Sq | $9.75 |
| 2090 Seventh Avenue | Harlem | $9.75 |
| 3427 Broadway | Hamilton Hts | $9.75 |
| 1501 Broadway | Times Square | $10.48 |
| 161 East 125th Street | East Harlem | $10.85 |
| 2818 Broadway | Upper West Side | $10.85 |
| 500 8th Avenue | Garment District | $10.97 |

- **The spread is real but not geographic.** Prices run from $9.75 to $10.97,
  about 12%. Uptown is not uniformly cheaper: East 125th St costs more than
  Herald Square, and the cheapest store near Times Square beats the Times
  Square store itself by 73¢. That's an argument for this tool rather than a
  rule of thumb.
- **These are delivery-menu prices.** They include Uber's markup but not its fees.
  The connector has no pickup mode and returns no fees. In-store prices are
  lower, and the markup may vary by store.
- **The connector has no store coordinates**, only an address embedded in the
  name ("Taco Bell (1501 Broadway Suite #7)"). Stores need geocoding.
- **The connector is only reachable through Claude**, not from this code.
  Ingest works on saved search responses. A Claude session or scheduled task
  runs the searches and saves the JSON, and `food-deals ingest` loads it.
- **Taco Bell's own site** (for pickup prices) is blocked by this cloud
  environment's network policy, so it isn't assessed yet. Nominatim and OSRM
  are blocked too, but Google Maps is reachable with a key.

## Usage

```bash
pip install -e ".[dev]"
food-deals ingest responses/*.json        # saved Uber Eats search responses
food-deals geocode                        # needs GOOGLE_MAPS_API_KEY; --dry-run lists queries
food-deals locate <store_id> <lat> <lon>  # or place a store by hand
food-deals rank "crunchwrap supreme" --chain "taco bell" --lat 40.7579 --lon -73.9855 --vot 20
```

`rank` orders stores by `price + walk minutes × value of time` (`--vot`, $/hr,
default 20; `--round-trip` to count the walk back). It estimates the walk as
straight-line distance × 1.3 at 5 km/h. Stores without coordinates are listed
last, by price.

Items match exactly after normalisation: "Crunchwrap Supreme®" matches
"crunchwrap supreme", but not "Crunchwrap Supreme® Combo".

## Next

1. Get a Google Maps key, then geocode the stores.
2. Set up a scheduled Claude task that runs connector searches over a grid of
   Manhattan addresses for a list of items and saves the responses for ingest.
3. Add pickup prices from first-party sources once a network that can reach
   them is available.
4. Build the web page: browser geolocation, a ranked list and a map.

```bash
pytest
```
