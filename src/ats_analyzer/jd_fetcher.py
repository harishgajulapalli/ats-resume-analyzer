"""Step 3: Get a job description from a web link.

Most job boards embed the posting as structured data (JSON-LD "JobPosting"),
which gives us the exact description. If that is missing, we fall back to the
page's main readable text.
"""

import json
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

MAX_BYTES = 5_000_000
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


class JobFetchError(ValueError):
    """Raised when a job description can't be fetched. Message is user-friendly."""


def fetch_job_description(url: str, timeout: int = 15) -> str:
    url = url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise JobFetchError("Please enter a full link starting with http:// or https://")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
        content = resp.raw.read(MAX_BYTES + 1, decode_content=True)
    except requests.RequestException as exc:
        raise JobFetchError(f"Could not open the link: {exc.__class__.__name__}") from exc

    if resp.status_code in (401, 403, 429, 999):
        raise JobFetchError(
            f"The site blocked automatic access (HTTP {resp.status_code}). "
            "Copy the job description and paste it as text instead."
        )
    if resp.status_code >= 400:
        raise JobFetchError(f"The link returned an error (HTTP {resp.status_code}).")
    if len(content) > MAX_BYTES:
        raise JobFetchError("The page is too large to process.")

    text = parse_job_html(content.decode(resp.encoding or "utf-8", errors="ignore"))
    if len(text.split()) < 30:
        raise JobFetchError(
            "Couldn't find a job description on that page (it may need a login or "
            "load content with JavaScript). Paste the description as text instead."
        )
    return text


def parse_job_html(html: str) -> str:
    """Extract the job description text from a job posting HTML page."""
    soup = BeautifulSoup(html, "html.parser")

    posting = _find_json_ld_job(soup)
    if posting:
        parts = [posting.get("title", "")]
        for key in ("description", "qualifications", "responsibilities", "skills",
                    "experienceRequirements", "educationRequirements"):
            value = posting.get(key)
            if isinstance(value, dict):
                value = value.get("description", "")
            if isinstance(value, list):
                value = "\n".join(map(str, value))
            if value:
                parts.append(_html_to_text(str(value)))
        text = "\n\n".join(p for p in parts if p)
        if len(text.split()) >= 30:
            return text

    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "form", "svg"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    return _tidy(main.get_text("\n"))


def _find_json_ld_job(soup: BeautifulSoup) -> dict | None:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        stack = [data]
        while stack:
            item = stack.pop()
            if isinstance(item, list):
                stack.extend(item)
            elif isinstance(item, dict):
                kind = item.get("@type")
                if kind == "JobPosting" or (isinstance(kind, list) and "JobPosting" in kind):
                    return item
                stack.extend(item.get("@graph", []))
    return None


def _html_to_text(fragment: str) -> str:
    return _tidy(BeautifulSoup(fragment, "html.parser").get_text("\n"))


def _tidy(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)
