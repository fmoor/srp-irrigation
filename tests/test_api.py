import datetime

import duckdb
import pandas
import pytest

from srp_irrigation import api


def as_list_of_dicts(r: duckdb.DuckDBPyRelation):
    return r.df().to_dict(orient="records")


@pytest.fixture
def con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    _ = con.execute("SET TimeZone = 'UTC'")
    api.migrate(con)
    return con


def test_upsert_subdivisions(con: duckdb.DuckDBPyConnection):
    # print_schema(con)
    input: list[api.Subdivision] = [
        {"id": 1, "name": "joe"},
        {"id": 2, "name": "sue"},
    ]
    now = datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)
    api.upsert_subdivisions(con, input, now)

    timestamps = {
        "first_seen_at": pandas.Timestamp(now),
        "last_seen_at": pandas.Timestamp(now),
        "last_scraped_at": pandas.NaT,
    }
    expected = [{**r, **timestamps, "id": str(r["id"])} for r in input]
    result = con.query("SELECT * FROM subdivision ORDER BY id")
    assert expected == as_list_of_dicts(result)

    input2: list[api.Subdivision] = [
        {
            "id": 1,
            "name": "joe-update",
        },
    ]
    now2 = datetime.datetime(2000, 1, 2, tzinfo=datetime.UTC)
    api.upsert_subdivisions(con, input2, now2)

    expected2 = [
        {
            "id": "1",
            "name": "joe-update",
            "first_seen_at": pandas.Timestamp(now),
            "last_seen_at": pandas.Timestamp(now2),
            "last_scraped_at": pandas.NaT,
        },
        {
            "id": "2",
            "name": "sue",
            **timestamps,
        },
    ]
    result2 = con.query("SELECT * FROM subdivision ORDER BY id")
    assert expected2 == as_list_of_dicts(result2)


def test_upsert_addresses(con: duckdb.DuckDBPyConnection):
    now1 = datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)
    api.upsert_subdivisions(con, [{"id": 1, "name": "joe"}], now1)

    input: api.Schedule = {
        "subdivisionId": 1,
        "scheduleDetails": [
            {
                "memberId": 3,
                "address": "123 N South St",
            },
            {
                "memberId": 5,
                "address": "456 E West Ave",
            },
        ],
    }

    now2 = datetime.datetime(2000, 1, 2, tzinfo=datetime.UTC)
    api.upsert_addresses(con, input, now2)

    timestamps = {
        "first_seen_at": pandas.Timestamp(now2),
        "last_seen_at": pandas.Timestamp(now2),
    }

    expected = [
        {
            "id": "3",
            "subdivision_id": "1",
            "address": "123 N South St",
            **timestamps,
        },
        {
            "id": "5",
            "subdivision_id": "1",
            "address": "456 E West Ave",
            **timestamps,
        },
    ]
    result = con.query("SELECT * FROM address ORDER BY id")
    assert expected == as_list_of_dicts(result)

    input2: api.Schedule = {
        "subdivisionId": 1,
        "scheduleDetails": [
            {
                "memberId": 5,
                "address": "8 St",
            },
        ],
    }
    now3 = datetime.datetime(2000, 1, 3, tzinfo=datetime.UTC)
    api.upsert_addresses(con, input2, now3)

    expected2 = [
        {
            "id": "3",
            "subdivision_id": "1",
            "address": "123 N South St",
            **timestamps,
        },
        {
            "id": "5",
            "subdivision_id": "1",
            "address": "8 St",
            "first_seen_at": pandas.Timestamp(now2),
            "last_seen_at": pandas.Timestamp(now3),
        },
    ]
    result2 = con.query("SELECT * FROM address ORDER BY id")
    assert expected2 == as_list_of_dicts(result2)
