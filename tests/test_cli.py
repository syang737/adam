from pathlib import Path

from food_deals import db
from food_deals.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
FILES = [str(FIXTURES / "ubereats_times_square.json"), str(FIXTURES / "ubereats_harlem.json")]
# Synthetic test coordinates, not geocoded: one store "here", one ~2km away.
HERE = (40.75, -73.99)
NEAR_ID = "e571314a-da34-4d54-acec-1950c2998f83"  # 500 8th Ave, $10.97
FAR_ID = "08b59a28-09e3-4900-8e43-f8f58c97ac6b"   # 976 6th Ave, $9.75


def run(tmp_path, *argv):
    return main(["--db", str(tmp_path / "t.sqlite"), *argv])


def test_ingest_then_rank(tmp_path, capsys):
    assert run(tmp_path, "ingest", *FILES, "--fetched-at", "2026-10-27T20:00:00+00:00") == 0
    run(tmp_path, "locate", NEAR_ID, *map(str, HERE))
    run(tmp_path, "locate", FAR_ID, str(HERE[0] + 2 / 111.2), str(HERE[1]))
    capsys.readouterr()

    argv = ["rank", "Crunchwrap Supreme®", "--chain", "taco bell", "--lat", str(HERE[0]), "--lon", str(HERE[1])]
    assert run(tmp_path, *argv, "--vot", "20") == 0
    lines = capsys.readouterr().out.splitlines()
    # 7 Taco Bells quote it; only the 2 placed ones are costed, and they come first.
    assert len(lines) == 7
    assert "500 8th Avenue" in lines[0] and "976 6th Avenue" in lines[1]
    assert all("(no location)" in line for line in lines[2:])

    run(tmp_path, *argv, "--vot", "0")
    assert "976 6th Avenue" in capsys.readouterr().out.splitlines()[0]


def test_reingest_keeps_coordinates(tmp_path):
    run(tmp_path, "ingest", *FILES)
    run(tmp_path, "locate", NEAR_ID, *map(str, HERE))
    run(tmp_path, "ingest", *FILES)
    conn = db.connect(tmp_path / "t.sqlite")
    assert NEAR_ID not in {s.source_store_id for s in db.unplaced(conn)}


def test_rank_uses_latest_snapshot(tmp_path, capsys):
    run(tmp_path, "ingest", FILES[0], "--fetched-at", "2026-10-01T00:00:00+00:00")
    conn = db.connect(tmp_path / "t.sqlite")
    with conn:
        conn.execute("update quotes set price_cents = 100 where source_store_id = ?", (NEAR_ID,))
    run(tmp_path, "ingest", FILES[0], "--fetched-at", "2026-10-27T00:00:00+00:00")
    pairs = db.latest_quotes(conn, "crunchwrap supreme", "taco bell", "delivery")
    near = [q for s, q in pairs if s.source_store_id == NEAR_ID]
    assert [q.price_cents for q in near] == [1097]


def test_geocode_dry_run_lists_queries(tmp_path, capsys):
    run(tmp_path, "ingest", FILES[1])
    capsys.readouterr()
    assert run(tmp_path, "geocode", "--dry-run") == 0
    out = capsys.readouterr().out
    assert "2090 Seventh Avenue, New York, NY" in out
    assert "203 W 125th Street, New York, NY" in out  # KFC: placed even with no prices yet
