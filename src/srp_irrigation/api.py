import datetime
import typing
from urllib.parse import quote

import duckdb
import requests

from . import browser

SUBDIVISIONS_URL = "https://water.gateway.srpnet.com/subdivisions/getsubdivisions/false"
SCHEDULE_URL = "https://water.gateway.srpnet.com/schedule/subdivision"
DATABASE_PATH = "data/srp-api.duckdb"
ADDRESS_SEARCH_URL = "https://water.gateway.srpnet.com/customer/address/search"


class Subdivision(typing.TypedDict):
    id: int
    name: str


class ScheduleDetail(typing.TypedDict):
    memberId: int
    address: str


class Schedule(typing.TypedDict):
    subdivisionId: int
    scheduleDetails: list[ScheduleDetail]


class Address(typing.TypedDict):
    waterAccountNumber: str
    completeAddress: str
    subdivisionId: int


def migrate(con: duckdb.DuckDBPyConnection):
    _ = con.execute("""
        CREATE TABLE IF NOT EXISTS subdivision (
            id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            first_seen_at TIMESTAMPTZ NOT NULL,
            last_seen_at TIMESTAMPTZ NOT NULL,
            last_scraped_at TIMESTAMPTZ
        );

        
        CREATE TABLE IF NOT EXISTS address (
            id VARCHAR PRIMARY KEY,
            subdivision_id VARCHAR REFERENCES subdivision(id),
            address VARCHAR NOT NULL,
            first_seen_at TIMESTAMPTZ NOT NULL,
            last_seen_at TIMESTAMPTZ NOT NULL
        );
    """)


def upsert_subdivisions(
    con: duckdb.DuckDBPyConnection,
    json: list[Subdivision],
    now: datetime.datetime,
):
    query = """
        INSERT INTO subdivision (
            id,
            name,
            first_seen_at,
            last_seen_at
        )
        SELECT
            s.value->>'id'::VARCHAR,
            s.value->>'name',
            $now,
            $now
        FROM json_each($subdivisions) AS s
        ON CONFLICT (id) DO UPDATE
        SET
            name = EXCLUDED.name,
            last_seen_at = EXCLUDED.last_seen_at
    """
    _ = con.execute(query, {"now": now, "subdivisions": json})


def as_list_of_dicts(r: duckdb.DuckDBPyRelation):
    return r.df().to_dict(orient="records")


def get_subdivisions_to_scrape(
    con: duckdb.DuckDBPyConnection,
    now: datetime.datetime,
) -> list[Subdivision]:
    query = """
        SELECT
            id,
            name
        FROM subdivision
        WHERE
            last_scraped_at < $now - INTERVAL '1 week'
            OR last_scraped_at IS NULL
    """
    result = con.sql(query, params={"now": now})
    return typing.cast(list[Subdivision], as_list_of_dicts(result))


def mark_subdivision_scraped(
    con: duckdb.DuckDBPyConnection,
    subdivision: Subdivision,
    now: datetime.datetime,
):
    query = """
        UPDATE subdivision
        SET last_scraped_at = $now
        WHERE id = $id
    """
    _ = con.execute(query, {"id": subdivision["id"], "now": now})


def upsert_addresses(
    con: duckdb.DuckDBPyConnection,
    json: Schedule,
    now: datetime.datetime,
):
    query = """
        INSERT INTO address (
            id,
            subdivision_id,
            address,
            first_seen_at,
            last_seen_at
        )
        SELECT
            d.value->>'memberId'::VARCHAR,
            $schedule->>'subdivisionId'::VARCHAR,
            d.value->>'address',
            $now,
            $now
        FROM json_each($schedule->'scheduleDetails') AS d
        ON CONFLICT (id) DO UPDATE
        SET
            subdivision_id = EXCLUDED.subdivision_id,
            address = EXCLUDED.address,
            last_seen_at = EXCLUDED.last_seen_at
    """
    _ = con.execute(query, {"now": now, "schedule": json})


def get_subdivisions() -> list[Subdivision]:
    browser.log("requesting subdivisions")
    rsp = requests.get(SUBDIVISIONS_URL)
    rsp.raise_for_status()
    browser.human_delay()
    return typing.cast(list[Subdivision], rsp.json())


def get_schedule(subdivision: Subdivision) -> Schedule:
    browser.log(f"requesting addresses for subdivision: {subdivision['name']}")
    rsp = requests.get(f"{SCHEDULE_URL}/{subdivision['id']}")
    if rsp.status_code == 404:
        return {
            "subdivisionId": subdivision["id"],
            "scheduleDetails": [],
        }
    rsp.raise_for_status()
    browser.human_delay()
    return typing.cast(Schedule, rsp.json())


def get_address(address: str) -> Address:
    rsp = requests.get(f"{ADDRESS_SEARCH_URL}/{quote(address)}")
    rsp.raise_for_status()
    browser.human_delay()
    return typing.cast(Address, rsp.json())


def now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def main():
    con = duckdb.connect(DATABASE_PATH)
    migrate(con)

    subdivisions = get_subdivisions()
    upsert_subdivisions(con, subdivisions, now())
    subdivisions = get_subdivisions_to_scrape(con, now())

    for i, subdivision in enumerate(subdivisions, start=1):
        print(f"{i} of {len(subdivisions)}")
        schedule = get_schedule(subdivision)
        try:
            _ = con.execute("BEGIN")
            upsert_addresses(con, schedule, now())
            mark_subdivision_scraped(con, subdivision, now())
            _ = con.execute("COMMIT")
        except:
            _ = con.execute("ROLLBACK")
