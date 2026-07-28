"""Configuration and environment loading for the UAE salon outreach workflow."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

SALONS_CSV = DATA_DIR / "salons.csv"
OUTREACH_CSV = DATA_DIR / "outreach_output.csv"

# --- Stage 1: Apify ---
APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN", "")

# Apify actor IDs in "owner~actor-name" form. Apify actor input schemas
# change over time -- check the actor's "Input" tab in the Apify Console if
# a run fails with a validation error.
#
# Note: apify/instagram-scraper's generic hashtag/place search (searchType)
# was tested and found unreliable -- it resolves through Google and can
# return an unrelated hashtag/location object instead of real posts. The
# dedicated hashtag-scraper actor below was verified to return real posts
# with owner usernames.
APIFY_ACTOR_HASHTAG = os.environ.get("APIFY_ACTOR_HASHTAG", "apify~instagram-hashtag-scraper")
APIFY_ACTOR_PROFILE = os.environ.get("APIFY_ACTOR_PROFILE", "apify~instagram-profile-scraper")

APIFY_POLL_INTERVAL_SECONDS = int(os.environ.get("APIFY_POLL_INTERVAL_SECONDS", "5"))
APIFY_RUN_TIMEOUT_SECONDS = int(os.environ.get("APIFY_RUN_TIMEOUT_SECONDS", "600"))

# Keep scrape volume modest by default. Instagram scraping via third-party
# tools sits in a gray area of Instagram's Terms of Service -- don't raise
# this without good reason, and see stage1_scrape.py's hard cap.
DEFAULT_SCRAPE_LIMIT = int(os.environ.get("SALON_SCRAPE_LIMIT", "25"))

# --- Stage 2: Anthropic ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
CLAUDE_REQUEST_DELAY_SECONDS = float(os.environ.get("CLAUDE_REQUEST_DELAY_SECONDS", "1.0"))

# --- Stage 3: Gmail drafts (optional) ---
GMAIL_CREDENTIALS_PATH = os.environ.get("GMAIL_CREDENTIALS_PATH", "")
GMAIL_TOKEN_PATH = os.environ.get("GMAIL_TOKEN_PATH", str(BASE_DIR / "gmail_token.json"))
GMAIL_SENDER = os.environ.get("GMAIL_SENDER", "me")
