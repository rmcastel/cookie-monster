"""
Fetch all active Crumbl store slugs.

When the carry-out page loads it fires a Next.js data request to
  crumblcookies.com/_next/data/<buildId>/en-US/stores.json
That response contains pageProps.allActiveStores — a full list of every
active location with slug, name, city, and state.
"""
import logging
from dataclasses import dataclass
from playwright.async_api import BrowserContext

from scraper.browser import collect_json_responses

log = logging.getLogger(__name__)

LOCATIONS_URL = "https://crumblcookies.com/order/carry_out"


@dataclass
class Store:
    slug: str
    name: str
    city: str | None
    state: str | None


def _is_stores_response(url: str, body: dict) -> bool:
    return (
        "_next/data" in url
        and "stores.json" in url
        and isinstance(body, dict)
        and "pageProps" in body
        and "allActiveStores" in body.get("pageProps", {})
    )


def _parse_stores(body: dict) -> list[Store]:
    stores = []
    for item in body["pageProps"]["allActiveStores"]:
        slug = item.get("slug")
        if not slug:
            continue
        stores.append(Store(
            slug=slug,
            name=item.get("name") or slug,
            city=item.get("city"),
            state=item.get("state"),
        ))
    return stores


async def get_all_stores(ctx: BrowserContext) -> list[Store]:
    page = await ctx.new_page()
    try:
        responses = await collect_json_responses(page, LOCATIONS_URL)
        for r in responses:
            if _is_stores_response(r["url"], r["body"]):
                stores = _parse_stores(r["body"])
                log.info("Found %d stores from %s", len(stores), r["url"])
                return stores
        log.error("stores.json response not found — captured URLs:\n%s",
                  "\n".join(r["url"] for r in responses))
        return []
    finally:
        await page.close()
