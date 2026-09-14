from __future__ import annotations

import random
import time

from playwright.sync_api import Page

SRP_URL = "https://water.srpnet.com/quick-view/schedule"


def log(message: str) -> None:
    print(f"[srp] {message}", flush=True)


def human_delay() -> None:
    """Wait 0.5–1.5 seconds between meaningful browser actions."""
    seconds = random.uniform(0.5, 1.5)
    log(f"Pausing {seconds:.2f} seconds...")
    time.sleep(seconds)


def open_page(page: Page) -> None:
    log(f"Opening {SRP_URL}")
    page.goto(SRP_URL, wait_until="domcontentloaded")
    log("Page reached DOMContentLoaded")

    log("Waiting for the SRP Angular app root")
    page.locator("app-root").wait_for(state="attached")

    # onetrust-reject-all-handler
    page.locator("#onetrust-reject-all-handler").click()

    # The initial schedule page does not contain the subdivision controls.
    # They are populated only after navigating via the top-nav Subdivision link.
    human_delay()


def select_subdivision_mode(page: Page) -> None:
    """Navigate to the Subdivision page and select subdivision-name search."""
    # SRP's navigation item is an <a> without an href, so it does not
    # receive the ARIA "link" role. Its SVG has the stable id nav-subdivision.
    log('Clicking top-navigation "Subdivision"')
    page.locator("a:has(> svg#nav-subdivision)").click()
    human_delay()

    log("Waiting for the subdivision page search controls")
    page.locator("mat-chip-list#mat-chip-list-0").wait_for(state="visible")

    chip = page.locator(
        "mat-chip-list#mat-chip-list-0 mat-chip"
    ).filter(has_text="Subdivision name")
    chip.click()
    human_delay()


def open_subdivision_dropdown(page: Page) -> None:
    log('Clicking "Select subdivision" dropdown')
    page.locator(
        'mat-select[formcontrolname="selectedNewSubdivision"]'
    ).click()


    log("Waiting for subdivision options in the Angular Material overlay")
    page.locator("mat-option").first.wait_for(state="visible")
    log("Subdivision options are visible")
    human_delay()


def select_subdivision(page: Page, name: str) -> None:
    """Open the dropdown and explicitly click the requested subdivision."""
    log("Opening the subdivision dropdown")
    select = page.locator(
        'mat-select[formcontrolname="selectedNewSubdivision"]'
    )
    select.wait_for(state="visible")
    select.click()

    log("Waiting for the subdivision options")
    option = page.locator("mat-option").filter(has_text=name).first
    option.wait_for(state="visible")

    # The options are rendered in an Angular Material overlay. With more
    # than 1,300 options, the requested option may not initially be in the
    # clickable viewport even though it exists in the DOM.
    log(f'Scrolling subdivision option {name!r} into view')
    option.scroll_into_view_if_needed()

    log(f"Clicking subdivision option {name!r}")
    # SRP's overlay can leave an option technically covered while it is
    # being positioned. Force the click only after explicitly scrolling
    # the real visible option into view.
    option.click(force=True)
    human_delay()


def click_view_schedule(page: Page) -> None:
    log('Finding "View schedule" button')
    button = page.get_by_role("button", name="View schedule")
    button.wait_for(state="visible")
    log('Clicking "View schedule"')
    button.click()

    log('Waiting for "Full schedule" to appear')
    page.get_by_role("heading", name="Full schedule", exact=True).first.wait_for(state="visible")
    log('"Full schedule" is visible')
    human_delay()
