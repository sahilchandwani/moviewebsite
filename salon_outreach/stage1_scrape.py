#!/usr/bin/env python3
"""
Stage 1: Scrape UAE salon Instagram data via Apify.

Two input modes:
  --handles handles.txt          One Instagram handle per line.
  --hashtag "dubaisalon,dubaihairstylist"
                                  Discover candidate handles from posts under
                                  one or more hashtags (comma-separated).

(A --location mode was tried and dropped: the generic Apify actor's
location/place search resolves through Google and returns location metadata
instead of real posts on this account, so it can't reliably find handles.
Use one or more relevant hashtags instead, e.g. #dubaisalon, #abudhabisalon,
#dubaihairstylist, #sharjahsalon.)

Hashtag discovery ends by running an Instagram profile scraper on the
resulting handles to pull display name, bio, external website link, and (if
publicly visible) a phone/WhatsApp number. Results are written to
data/salons.csv with columns: handle, name, bio, website, phone, whatsapp,
email. Fields are left blank rather than guessed when nothing is found.

Keep --limit modest (hard-capped at 100 per run below). Instagram scraping
via third-party tools sits in a gray area of Instagram's Terms of Service --
this script does not paginate beyond what you ask for and makes no attempt
to bypass rate limits, logins, or blocks.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests

import config
from utils import extract_contact_info, fetch_website_text, write_csv

APIFY_BASE = "https://api.apify.com/v2"
TERMINAL_STATUSES = ("SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED")

FIELDNAMES = ["handle", "name", "bio", "website", "phone", "whatsapp", "email"]


def run_apify_actor(actor_id: str, run_input: dict) -> list[dict]:
    """Start an Apify actor run, poll until it finishes, return dataset items."""
    if not config.APIFY_API_TOKEN:
        sys.exit("APIFY_API_TOKEN is not set. Copy .env.example to .env and fill it in.")

    start = requests.post(
        f"{APIFY_BASE}/acts/{actor_id}/runs",
        params={"token": config.APIFY_API_TOKEN},
        json=run_input,
        timeout=30,
    )
    start.raise_for_status()
    run = start.json()["data"]
    run_id = run["id"]

    deadline = time.monotonic() + config.APIFY_RUN_TIMEOUT_SECONDS
    status = run["status"]
    while status not in TERMINAL_STATUSES:
        if time.monotonic() > deadline:
            sys.exit(f"Apify run {run_id} did not finish within {config.APIFY_RUN_TIMEOUT_SECONDS}s")
        time.sleep(config.APIFY_POLL_INTERVAL_SECONDS)
        poll = requests.get(
            f"{APIFY_BASE}/actor-runs/{run_id}",
            params={"token": config.APIFY_API_TOKEN},
            timeout=30,
        )
        poll.raise_for_status()
        run = poll.json()["data"]
        status = run["status"]
        print(f"  Apify run {run_id}: {status}...")

    if status != "SUCCEEDED":
        sys.exit(f"Apify run {run_id} ended with status {status} -- check the run in the Apify Console.")

    dataset_id = run["defaultDatasetId"]
    items = requests.get(
        f"{APIFY_BASE}/datasets/{dataset_id}/items",
        params={"token": config.APIFY_API_TOKEN, "format": "json"},
        timeout=60,
    )
    items.raise_for_status()
    return items.json()


def discover_handles_by_hashtag(hashtags: list[str], limit: int) -> list[str]:
    """Search one or more hashtags for posts, return unique owner handles.

    `limit` is the number of *unique salons* wanted, not raw posts -- the
    same salon often has several posts under a hashtag, so we ask for more
    raw posts than `limit` and dedupe down to unique owners. If we still
    come up short, more/different hashtags usually help more than a bigger
    raw fetch, since duplicate owners inflate the raw count without adding
    new handles.
    """
    clean_tags = [t.strip().lstrip("#") for t in hashtags if t.strip()]
    raw_fetch_limit = min(limit * 4, 500)
    print(
        f"Searching Instagram hashtag(s) {clean_tags} "
        f"(fetching up to {raw_fetch_limit} posts to find {limit} unique salon(s))..."
    )
    run_input = {
        "hashtags": clean_tags,
        "resultsType": "posts",
        "resultsLimit": raw_fetch_limit,
    }
    items = run_apify_actor(config.APIFY_ACTOR_HASHTAG, run_input)

    handles: list[str] = []
    for item in items:
        handle = (
            item.get("ownerUsername")
            or item.get("username")
            or (item.get("owner") or {}).get("username")
        )
        if handle and handle not in handles:
            handles.append(handle)
        if len(handles) >= limit:
            break

    if len(handles) < limit:
        print(
            f"Note: only found {len(handles)} unique handle(s) from {len(items)} post(s) -- "
            "try adding more hashtags or raising the raw fetch further."
        )
    return handles[:limit]


def scrape_profiles(handles: list[str], fetch_websites: bool) -> list[dict]:
    print(f"Fetching profile details for {len(handles)} handle(s)...")
    run_input = {"usernames": handles}
    items = run_apify_actor(config.APIFY_ACTOR_PROFILE, run_input)

    rows = []
    for item in items:
        handle = item.get("username") or item.get("handle") or ""
        name = item.get("fullName") or item.get("name") or ""
        bio = (item.get("biography") or item.get("bio") or "").replace("\n", " ").strip()

        # externalUrl is a plain string; externalUrls (plural) is a list of
        # {title, url, lynx_url, link_type} objects -- pull .url out of it.
        external_urls = item.get("externalUrls") or []
        first_external_url = external_urls[0].get("url", "") if external_urls and isinstance(external_urls[0], dict) else ""
        website = item.get("externalUrl") or first_external_url or item.get("website") or ""

        website_text = fetch_website_text(website) if (fetch_websites and website) else ""
        # Some salons put a wa.me/api.whatsapp.com link directly in the
        # "website" field instead of a real site -- pass the raw URL through
        # too so that link itself is recognized, since fetching it as a
        # webpage returns nothing useful.
        contact = extract_contact_info(bio, website_text, website)

        # Some Apify plans/actor versions expose structured business-contact
        # fields (phone/email) -- prefer those over regex-extracted values
        # when present. On a free Apify plan these are typically absent, so
        # contact info comes from the bio/website regex fallback instead.
        phone = item.get("businessPhoneNumber") or item.get("publicPhoneNumber") or contact["phone"]
        whatsapp = item.get("whatsappNumber") or contact["whatsapp"]
        email = item.get("businessEmail") or item.get("publicEmail") or contact["email"]

        rows.append(
            {
                "handle": handle,
                "name": name,
                "bio": bio,
                "website": website,
                "phone": phone,
                "whatsapp": whatsapp,
                "email": email,
            }
        )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--handles", help="Path to a text file with one Instagram handle per line")
    mode.add_argument("--hashtag", help="One or more hashtags to search, comma-separated (with or without #)")
    parser.add_argument(
        "--limit",
        type=int,
        default=config.DEFAULT_SCRAPE_LIMIT,
        help=f"Max number of salons to collect (default: {config.DEFAULT_SCRAPE_LIMIT}; keep this modest)",
    )
    parser.add_argument(
        "--no-fetch-websites",
        action="store_true",
        help="Skip fetching each salon's own website (faster, but misses phone/email only listed there)",
    )
    parser.add_argument("--out", default=str(config.SALONS_CSV), help="Output CSV path")
    args = parser.parse_args()

    if args.limit > 100:
        sys.exit("Refusing to scrape more than 100 profiles in one run -- keep volume modest.")

    if args.handles:
        with open(args.handles, encoding="utf-8") as f:
            handles = [line.strip().lstrip("@") for line in f if line.strip()]
        handles = handles[: args.limit]
    else:
        handles = discover_handles_by_hashtag(args.hashtag.split(","), args.limit)

    if not handles:
        sys.exit("No handles found -- nothing to scrape.")

    rows = scrape_profiles(handles, fetch_websites=not args.no_fetch_websites)
    write_csv(Path(args.out), rows, FIELDNAMES)
    print(f"Wrote {len(rows)} salon(s) to {args.out}")

    missing_contact = [r["handle"] for r in rows if not (r["phone"] or r["whatsapp"] or r["email"])]
    if missing_contact:
        print(f"Note: no phone/WhatsApp/email found for: {', '.join(missing_contact)}")


if __name__ == "__main__":
    main()
