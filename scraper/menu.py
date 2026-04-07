"""
Scrape weekly + classic cookie flavors for a single Crumbl store.

When a store page loads it fires a GraphQL request to pos.crumbl.com/graphql.
The response path that contains the menu is:
  data.public.sourceForStore.productSummary.options

Each option represents one cookie flavor:
  option.metadata.cookieId   → unique cookie ID
  option.name                → display name
  option.metadata.isClassicMenu
      False  → weekly (rotating) flavor
      True   → classic (permanent) flavor
"""
import logging
from dataclasses import dataclass
from playwright.async_api import BrowserContext, Page

from scraper.browser import collect_json_responses

log = logging.getLogger(__name__)

BASE_URL = "https://crumblcookies.com/order/carry_out/{slug}"
POS_GRAPHQL_HOST = "pos.crumbl.com/graphql"


@dataclass
class Cookie:
    cookie_id: str
    cookie_name: str
    flavor_type: str  # 'weekly' or 'classic'
    secret_menu: str
    cal_count: int


def _is_menu_response(url: str, body: dict) -> bool:
    if POS_GRAPHQL_HOST not in url:
        return False
    try:
        body["data"]["public"]["sourceForStore"]["productSummary"]["options"]
        return True
    except (KeyError, TypeError):
        return False


def _parse_menu(body: dict) -> list[Cookie]:
    options = body["data"]["public"]["sourceForStore"]["productSummary"]["options"]
    cookies = []
    for item in options:
        opt = item.get("option", {})
        metadata = opt.get("metadata") or {}

        cookie_id = metadata.get("cookieId")
        name = opt.get("name")
        secret_menu = opt.get("tagName", False)
        cal_count = (metadata.get("calorieInformation") or {}).get("total")

        # Skip non-cookie items (drinks, gift cards, etc.) and mini-size duplicates
        if not cookie_id or not name:
            continue
        if cookie_id.endswith("-mini"): # remove mini cookies
            continue

        is_classic = metadata.get("isClassicMenu", False)
        flavor_type = "classic" if is_classic else "weekly"

        cookies.append(Cookie(
            cookie_id=cookie_id,
            cookie_name=name,
            flavor_type=flavor_type,
            secret_menu = secret_menu,
            cal_count = cal_count,
        ))
    return cookies


async def get_store_menu(ctx: BrowserContext, slug: str, page: Page | None = None) -> list[Cookie]:
    url = BASE_URL.format(slug=slug)
    owned = page is None
    if owned:
        page = await ctx.new_page()
    try:
        responses = await collect_json_responses(page, url)
        for r in responses:
            if _is_menu_response(r["url"], r["body"]):
                cookies = _parse_menu(r["body"])
                log.debug("Store %s: %d cookie(s)", slug, len(cookies))
                return cookies
        log.warning("No menu response found for store '%s'", slug)
        return []
    finally:
        if owned:
            await page.close()
