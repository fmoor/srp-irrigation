from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import duckdb

from .scraper import Address, Subdivision


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def connect(database_path: Path) -> duckdb.DuckDBPyConnection:
    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = duckdb.connect(str(database_path))

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS subdivisions (
            subdivision_id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            first_seen_at TIMESTAMPTZ NOT NULL,
            last_seen_at TIMESTAMPTZ NOT NULL
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS addresses (
            address_id VARCHAR PRIMARY KEY,
            subdivision_id VARCHAR NOT NULL,
            address VARCHAR NOT NULL,
            first_seen_at TIMESTAMPTZ NOT NULL,
            last_seen_at TIMESTAMPTZ NOT NULL
        )
        """
    )

    # Migrate databases created by earlier versions, whose timestamps were
    # TIMESTAMP values containing UTC clock time but no timezone.
    for table in ("subdivisions", "addresses"):
        for column in ("first_seen_at", "last_seen_at"):
            column_type = connection.execute(
                """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name = ? AND column_name = ?
                """,
                [table, column],
            ).fetchone()

            if column_type and column_type[0] == "TIMESTAMP":
                connection.execute(
                    f"""
                    ALTER TABLE {table}
                    ALTER COLUMN {column}
                    SET DATA TYPE TIMESTAMPTZ
                    USING {column} AT TIME ZONE 'UTC'
                    """
                )

    return connection


def make_address_id(address: Address) -> str:
    """Temporary identity scheme until SRP exposes an address ID."""
    normalized = " ".join(address.address.upper().split())
    return f"{address.subdivision_id}:{normalized}"


def save_subdivision(
    connection: duckdb.DuckDBPyConnection,
    subdivision: Subdivision,
) -> None:
    now = utc_now()

    connection.execute(
        """
        INSERT INTO subdivisions (
            subdivision_id,
            name,
            first_seen_at,
            last_seen_at
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT (subdivision_id)
        DO UPDATE SET
            name = excluded.name,
            last_seen_at = excluded.last_seen_at
        """,
        [
            subdivision.external_id,
            subdivision.name,
            now,
            now,
        ],
    )


def save_address(
    connection: duckdb.DuckDBPyConnection,
    address: Address,
) -> None:
    now = utc_now()
    address_id = make_address_id(address)

    connection.execute(
        """
        INSERT INTO addresses (
            address_id,
            subdivision_id,
            address,
            first_seen_at,
            last_seen_at
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (address_id)
        DO UPDATE SET
            last_seen_at = excluded.last_seen_at
        """,
        [
            address_id,
            address.subdivision_id,
            address.address,
            now,
            now,
        ],
    )
