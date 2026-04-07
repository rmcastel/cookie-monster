"""
Cookie Monster — full weekly scrape.

Usage:
    python main.py                  # scrape all stores
    python main.py --limit 10       # scrape first 10 stores (for testing)
    python main.py --concurrency 3  # number of parallel store pages (default 3)
"""
import argparse
import asyncio
import logging
from datetime import date, timedelta

from playwright.async_api import async_playwright

from db import init_db, get_db, upsert_store, insert_menu_item
from scraper.browser import make_context
from scraper.locations import get_all_stores
from scraper.menu import get_store_menu

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Default seconds between finishing one store and starting the next (per worker)
REQUEST_DELAY = 2.0


def current_week_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())  # Monday = 0


async def scrape_store(ctx, db, slug: str, week_of: date, delay: float) -> int:
    """Scrape one store and write results to db. Returns number of cookies inserted."""
    page = await ctx.new_page()
    try:
        cookies = await get_store_menu(ctx, slug, page=page)
        count = 0
        for c in cookies:
            await insert_menu_item(db, week_of, slug, c.cookie_id, c.cookie_name, c.flavor_type, c.secret_menu, c.cal_count)
            count += 1
        await db.commit()
        await asyncio.sleep(delay)
        return count
    finally:
        await page.close()


async def run(limit: int | None, concurrency: int) -> None:
    week_of = current_week_monday()
    log.info("Week of: %s", week_of)

    await init_db()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await make_context(browser)
        db = await get_db()

        try:
            # Phase 1 — discover stores
            log.info("Discovering stores...")
            stores = await get_all_stores(ctx)
            if not stores:
                log.error("No stores found. Run discover.py first to debug.")
                return
            log.info("Found %d store(s)", len(stores))

            if limit:
                stores = stores[:limit]
                log.info("Limiting to %d store(s)", limit)

            # Persist store records
            for s in stores:
                await upsert_store(db, s.slug, s.name, s.city, s.state)
            await db.commit()

            # Phase 2 — scrape menus with bounded concurrency
            sem = asyncio.Semaphore(concurrency)

            async def bounded(store):
                async with sem:
                    try:
                        cookies = await scrape_store(ctx, db, store.slug, week_of, REQUEST_DELAY)
                        log.info("  %-30s  %d cookie(s)", store.slug, cookies)
                    except Exception as e:
                        log.warning("  %-30s  SKIPPED — %s", store.slug, e)

            tasks = [asyncio.create_task(bounded(s)) for s in stores]
            await asyncio.gather(*tasks)

        finally:
            await db.close()
            await browser.close()

    log.info("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Crumbl Cookie menus")
    parser.add_argument("--limit",       type=int, default=None, help="Max stores to scrape")
    parser.add_argument("--concurrency", type=int, default=3,    help="Parallel store pages")
    args = parser.parse_args()
    asyncio.run(run(args.limit, args.concurrency))


if __name__ == "__main__":
    main()
