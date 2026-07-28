"""Shared helpers: CSV IO and best-effort contact-info extraction.

Contact extraction only ever returns values that literally appear in the
source text (bio / website) -- it never guesses or fabricates a phone,
WhatsApp number, or email.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup

# UAE mobile numbers: +971 5X XXX XXXX / 05X XXX XXXX (spacing/dashes vary).
UAE_PHONE_RE = re.compile(r"(?:\+?971[\s-]?|0)5\d(?:[\s-]?\d){7}")
# Looser international fallback for numbers that aren't UAE-formatted.
GENERIC_PHONE_RE = re.compile(r"\+\d{1,3}[\s-]?\(?\d{1,4}\)?(?:[\s-]?\d{2,4}){2,4}")
WHATSAPP_LINK_RE = re.compile(
    r"(?:wa\.me/|(?:api\.)?whatsapp\.com/send\?phone=)\+?(\d{7,15})",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


def extract_contact_info(*texts: str) -> dict:
    """Pull phone / whatsapp / email out of one or more text blobs.

    Only returns values that literally appear in the text -- leaves a field
    blank rather than guessing.
    """
    combined = "\n".join(t for t in texts if t)
    result = {"phone": "", "whatsapp": "", "email": ""}

    wa_match = WHATSAPP_LINK_RE.search(combined)
    if wa_match:
        result["whatsapp"] = wa_match.group(1)
    elif "whatsapp" in combined.lower():
        # Bios often say "WhatsApp: +971..." without a wa.me link -- pull the
        # nearest phone-shaped match after the word "whatsapp".
        near = combined.lower().split("whatsapp", 1)[1][:60]
        m = UAE_PHONE_RE.search(near) or GENERIC_PHONE_RE.search(near)
        if m:
            result["whatsapp"] = m.group(0).strip()

    phone_match = UAE_PHONE_RE.search(combined) or GENERIC_PHONE_RE.search(combined)
    if phone_match:
        candidate = phone_match.group(0).strip()
        if candidate != result["whatsapp"]:
            result["phone"] = candidate

    email_match = EMAIL_RE.search(combined)
    if email_match:
        result["email"] = email_match.group(0)

    return result


def fetch_website_text(url: str, timeout: int = 8) -> str:
    """Best-effort fetch of a salon's own website homepage text.

    Failures are swallowed -- a slow or broken third-party site should not
    crash the scrape. Returns "" on any error.
    """
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SalonOutreachBot/1.0)"},
        )
        resp.raise_for_status()
    except requests.RequestException:
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")
    # tel:/mailto:/wa.me link targets are often the cleanest signal, and a
    # plain visible-text regex would miss anything tucked into an href only.
    hrefs = " ".join(
        a["href"]
        for a in soup.find_all("a", href=True)
        if a["href"].startswith(("tel:", "mailto:", "https://wa.me", "https://api.whatsapp.com"))
    )
    return soup.get_text(" ", strip=True)[:5000] + " " + hrefs


def write_csv(path: str | Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def read_csv(path: str | Path) -> list[dict]:
    path = Path(path)
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
