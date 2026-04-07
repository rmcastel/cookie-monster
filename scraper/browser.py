"""
Shared Playwright browser utilities.
"""
import asyncio
import json
from typing import Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Response

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

# Seconds to wait after networkidle before giving up on extra lazy-loaded calls
SETTLE_MS = 2_500


async def collect_json_responses(page: Page, url: str, timeout_ms: int = 45_000) -> list[dict[str, Any]]:
    """
    Navigate to *url*, wait for network to go idle, then return every JSON
    API response that fired during the load as a list of dicts:
        [{"url": str, "status": int, "body": Any}, ...]
    """
    collected: list[dict[str, Any]] = []

    async def on_response(response: Response) -> None:
        ct = response.headers.get("content-type", "")
        if "json" not in ct:
            return
        try:
            body = await response.json()
            collected.append({"url": response.url, "status": response.status, "body": body})
        except Exception:
            pass

    page.on("response", on_response)
    await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
    await page.wait_for_timeout(SETTLE_MS)
    return collected


async def make_context(browser: Browser) -> BrowserContext:
    ctx = await browser.new_context(
        extra_http_headers=HEADERS,
        locale="en-US",
        timezone_id="America/Denver",  # Crumbl HQ timezone
    )
    return ctx


async def launch_browser():
    """Async context manager that yields a ready-to-use Browser."""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            yield browser
        finally:
            await browser.close()
