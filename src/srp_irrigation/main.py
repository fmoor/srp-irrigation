from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

from .browser import log, open_page, select_subdivision_mode
from .database import connect, save_address, save_subdivision
from .scraper import get_schedule_addresses, get_subdivisions

DATABASE_PATH = Path("data/srp.duckdb")
DEBUG_DIRECTORY = Path("data/debug")


def save_debug_artifacts(page, error: BaseException) -> None:
    DEBUG_DIRECTORY.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%fZ")
    dom_path = DEBUG_DIRECTORY / f"dom-error-{timestamp}.html"
    screenshot_path = DEBUG_DIRECTORY / f"screenshot-error-{timestamp}.png"

    log("Saving the current DOM before closing Firefox")
    try:
        dom_path.write_text(page.content(), encoding="utf-8")
        log(f"Saved error DOM to {dom_path}")
    except Exception as debug_error:
        log(f"Could not save DOM: {debug_error}")

    try:
        page.screenshot(path=str(screenshot_path), full_page=True)
        log(f"Saved error screenshot to {screenshot_path}")
    except Exception as debug_error:
        log(f"Could not save screenshot: {debug_error}")


def main() -> None:
    log("Starting SRP irrigation scraper")
    database = connect(DATABASE_PATH)
    log(f"Using database {DATABASE_PATH}")

    with sync_playwright() as playwright:
        log("Launching visible Firefox")
        browser = playwright.firefox.launch(headless=False)
        page = browser.new_page()

        try:
            open_page(page)
            select_subdivision_mode(page)

            subdivisions = get_subdivisions(page)
            log(f"Found {len(subdivisions)} subdivisions")

            successful = 0
            failed = 0
            total_addresses = 0

            for index, subdivision in enumerate(subdivisions, start=1):
                log(f"Processing subdivision {index}/{len(subdivisions)}")
                try:
                    database.begin()
                    save_subdivision(database, subdivision)
                    addresses = get_schedule_addresses(page, subdivision)

                    for address in addresses:
                        save_address(database, address)

                    database.commit()
                    successful += 1
                    total_addresses += len(addresses)
                    log(
                        f"Subdivision {index}/{len(subdivisions)} "
                        f"completed: {len(addresses)} addresses saved"
                    )

                except Exception as error:
                    failed += 1
                    try:
                        database.rollback()
                    except Exception as rollback_error:
                        log(f"Could not roll back subdivision transaction: {rollback_error!r}")
                    log(
                        f"ERROR processing subdivision "
                        f"{index}/{len(subdivisions)}: {error!r}"
                    )
                    save_debug_artifacts(page, error)
                    continue

            log(
                f"Run complete: {successful} subdivisions succeeded, "
                f"{failed} failed, {total_addresses} addresses observed"
            )

        except Exception as error:
            log(f"ERROR: scraper failed: {error!r}")
            save_debug_artifacts(page, error)
            raise

        finally:
            log("Closing Firefox")
            browser.close()
            database.close()
            log("Firefox closed")
            log("Database closed")


if __name__ == "__main__":
    main()
