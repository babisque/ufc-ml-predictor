"""
ufcstats.com sits behind a JS proof-of-work anti-bot check ("Checking your
browser..."). A plain `requests.get` only ever receives that stub page since
it can't execute the challenge script.

`request_get` is a drop-in replacement for `requests.get`: on first use it
drives a real headless browser through the challenge once via Playwright,
lifts the resulting clearance cookies into a `requests.Session`, and caches
that session at module level so the rest of a scrape (and any later calls in
the same process) can use fast plain HTTP instead of a browser per page.
"""
import requests
from playwright.sync_api import sync_playwright

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)
CHALLENGE_ENTRY_URL = "http://ufcstats.com/statistics/events/completed?page=all"
CHALLENGE_WAIT_SELECTOR = "tr.b-statistics__table-row"
CHALLENGE_MARKER = "Checking your browser"

_session = None


def _solve_challenge(timeout: int = 30000) -> requests.Session:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        page.goto(CHALLENGE_ENTRY_URL, timeout=timeout)
        page.wait_for_selector(CHALLENGE_WAIT_SELECTOR, timeout=timeout)
        cookies = context.cookies()
        browser.close()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    for cookie in cookies:
        session.cookies.set(
            cookie["name"], cookie["value"],
            domain=cookie.get("domain"), path=cookie.get("path", "/"),
        )
    return session


def request_get(url: str, headers: dict = None, timeout: int = 10) -> requests.Response:
    global _session
    if _session is None:
        _session = _solve_challenge()

    merged_headers = {**_session.headers, **(headers or {})}
    response = _session.get(url, headers=merged_headers, timeout=timeout)

    if CHALLENGE_MARKER in response.text[:2000]:
        _session = _solve_challenge()
        merged_headers = {**_session.headers, **(headers or {})}
        response = _session.get(url, headers=merged_headers, timeout=timeout)

    return response
