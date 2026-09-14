from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Page

from .browser import (
    click_view_schedule,
    open_subdivision_dropdown,
    select_subdivision,
)


@dataclass
class Subdivision:
    external_id: str
    name: str


@dataclass
class Address:
    address: str
    subdivision_id: str
    subdivision_name: str


def get_subdivisions(page: Page) -> list[Subdivision]:
    """Read all subdivision options from the dropdown."""
    open_subdivision_dropdown(page)

    options = page.locator("mat-option")
    subdivisions: list[Subdivision] = []

    for option in options.all():
        name = option.inner_text().strip()

        if not name:
            continue

        # Temporary until we verify the actual SRP option ID.
        external_id = option.get_attribute("value")
        if external_id is None:
            external_id = name

        subdivisions.append(
            Subdivision(
                external_id=str(external_id),
                name=name,
            )
        )

    page.keyboard.press("Escape")
    return subdivisions


def get_schedule_addresses(
    page: Page,
    subdivision: Subdivision,
) -> list[Address]:
    """Select a subdivision and extract its displayed addresses."""
    select_subdivision(page, subdivision.name)
    click_view_schedule(page)

    table = page.locator("table").filter(has_text="Address").first
    rows = table.locator("tbody tr")

    addresses: list[Address] = []

    for row in rows.all():
        cells = row.locator("td")

        if cells.count() == 0:
            continue

        address = cells.nth(0).inner_text().strip()

        # SRP displays the ditch as a schedule row, not an address.
        if address == "Ditch":
            continue

        if not address:
            continue

        addresses.append(
            Address(
                address=address,
                subdivision_id=subdivision.external_id,
                subdivision_name=subdivision.name,
            )
        )

    return addresses
