# UAE Salon Outreach Workflow

A three-stage Python workflow for reaching out to UAE hair/beauty salons
about a white-label signature-perfume offering:

1. **Scrape** salon Instagram data via Apify → `data/salons.csv`
2. **Generate** three outreach messages per salon (Instagram DM, follow-up
   email, WhatsApp message) via the Anthropic API → `data/outreach_output.csv`
3. **Output** a day-by-day sending checklist, and optionally create Gmail
   drafts for the follow-up emails

Each stage is a standalone script so you can re-run just one at a time
(e.g. re-generate messages without re-scraping, or re-run stage 3 after
tweaking the CSV by hand).

> ⚠️ **Read this before running Stage 1.** Scraping Instagram through a
> third-party tool like Apify sits in a gray area of Instagram's Terms of
> Service. This project deliberately:
> - Defaults to a modest scrape limit (`SALON_SCRAPE_LIMIT`, default 25) and
>   hard-caps any single run at 100 profiles.
> - Does **not** post, message, or take any automated action on Instagram —
>   it only reads public profile data.
> - Does **not** auto-send anything on Instagram or WhatsApp. There's no
>   general-purpose API for either, and nothing here tries to work around
>   that — those two channels are always sent manually, by you, from your
>   own accounts.
>
> Use your own judgment about volume and frequency, and consider Instagram's
> ToS and rate limits your responsibility, not something this script manages
> for you.

## Setup

```bash
cd salon_outreach
python3 -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

| Variable | Required for | Notes |
|---|---|---|
| `APIFY_API_TOKEN` | Stage 1 | From your [Apify account settings](https://console.apify.com/account/integrations) |
| `ANTHROPIC_API_KEY` | Stage 2 | From the [Anthropic Console](https://console.anthropic.com/) |
| `GMAIL_CREDENTIALS_PATH` / `GMAIL_TOKEN_PATH` | Stage 3 (optional) | See [Gmail setup](#optional-gmail-draft-creation) below |

`CLAUDE_MODEL` defaults to `claude-sonnet-4-6` (as requested). Swap it to a
different Claude model ID any time by setting `CLAUDE_MODEL` in `.env` — the
code doesn't hardcode it anywhere else.

## Stage 1 — Scrape

```bash
# From a list of known handles, one per line, no leading @ needed (either works)
python stage1_scrape.py --handles my_handles.txt --limit 20

# Or discover candidates from one or more hashtags (comma-separated)
python stage1_scrape.py --hashtag "dubaisalon,dubaihairstylist" --limit 20
```

This runs the configured Apify actors (default `apify/instagram-hashtag-scraper`
for hashtag discovery, `apify/instagram-profile-scraper` for profile details —
both overridable via `.env`), pulls each salon's public bio, display name,
and external website link, and does a lightweight best-effort fetch of that
website's homepage to look for a phone/WhatsApp number or email if one
wasn't already in the bio. Nothing is guessed: if a field isn't literally
present in the bio or on the website, it's left blank in the CSV.

Output: `data/salons.csv` with columns
`handle, name, bio, website, phone, whatsapp, email`.

**Why no `--location` mode:** an earlier version of this script supported
searching by location via `apify/instagram-scraper`'s generic `place` search
type. Live testing found that search resolves through Google and can return
an unrelated location's metadata instead of real posts, so it was dropped
rather than shipped as a silently-broken feature. Use a handful of relevant
hashtags instead (e.g. `dubaisalon`, `abudhabisalon`, `dubaihairstylist`,
`sharjahsalon`) — this was verified to return real posts with real owner
handles.

**If a run fails validation:** Apify actor input schemas change over time.
Open the actor's "Input" tab in the [Apify Console](https://console.apify.com/actors)
and adjust the `run_input` dict in `stage1_scrape.py` to match.

## Stage 2 — Generate messages

```bash
python stage2_generate.py
```

Reads `data/salons.csv`, calls the Anthropic API once per salon, and asks
for three messages that follow the pitch: salons already have clients
sitting in the chair for a long visit — a branded, signature perfume with
the salon's name on it turns that dead time into recurring revenue and
client loyalty, offered white-label/UAE-made/low-MOQ/flexible terms. The
Instagram DM opener is deliberately varied per salon (via a higher sampling
temperature and prompting to personalize using the salon's name/bio) so
they don't all read like the same template.

Output: `data/outreach_output.csv` — the original columns plus:

- `instagram_dm`
- `follow_up_email_subject`, `follow_up_email_body`
- `whatsapp_message`
- `missing_channels` — comma-separated list of `phone`, `whatsapp`, and/or
  `email` that came back blank from Stage 1, so you know which touchpoints
  won't work for that salon

If generation fails for a row (rate limit exhausted, a refusal, or
unparseable output), that row's message columns are left blank and a
warning is printed — the rest of the run continues.

## Stage 3 — Output / scheduling reminder

```bash
python stage3_output.py
```

Reads `data/outreach_output.csv` and always prints a day-by-day CLI
checklist:

```
Day 1 — send these Instagram DMs manually: ...
Day 2 — follow-up emails: ...
Day 4 — send these WhatsApp messages manually: ...
```

plus a list of any salons flagged with missing touchpoints.

### Optional: Gmail draft creation

**If you're running this via Claude Code with a Gmail connector already
attached to the session**, you don't need any of the OAuth setup below —
Claude can create drafts directly through that connector after Stage 2
finishes. The OAuth path here is for running `stage3_output.py` completely
standalone (no Claude in the loop).

If `GMAIL_CREDENTIALS_PATH` and `GMAIL_TOKEN_PATH` are both set in `.env`,
Stage 3 will instead create a **Gmail draft** (never sent automatically) for
each salon's follow-up email that has an email address:

1. In the [Google Cloud Console](https://console.cloud.google.com/), create
   a project, enable the **Gmail API**, and create an OAuth **Desktop app**
   client. Download the JSON as `client_secret.json` and point
   `GMAIL_CREDENTIALS_PATH` at it.
2. The first time you run `stage3_output.py`, it will open a browser for you
   to authorize your Google account (scope: `gmail.compose` only — it can
   create drafts, nothing else). The resulting token is cached at
   `GMAIL_TOKEN_PATH` (default `./gmail_token.json`) and reused after that.
3. Drafts land in your Gmail **Drafts** folder, dated day 2 of the sequence.

> **Important limitation:** the Gmail API has no "send later"/schedule field
> on drafts — this only *creates* the draft. You (or your own reminder/
> calendar entry) still need to actually send it on day 2. Nothing in this
> project auto-sends email.

If Gmail isn't configured, Stage 3 just skips draft creation and prints the
subject + recipient for each follow-up email as part of the Day 2 section,
so you can send them however you like.

## Running all three stages at once

```bash
python main.py --hashtag dubaisalon --limit 20
```

`main.py` is a thin wrapper that shells out to the three stage scripts in
order. Prefer calling `stage1_scrape.py` / `stage2_generate.py` /
`stage3_output.py` directly when you only need to re-run one stage.

## File layout

```
salon_outreach/
├── config.py            # env var loading, defaults
├── utils.py              # CSV helpers + contact-info extraction
├── stage1_scrape.py       # Stage 1: Apify → data/salons.csv
├── stage2_generate.py     # Stage 2: Anthropic → data/outreach_output.csv
├── stage3_output.py       # Stage 3: CLI checklist + optional Gmail drafts
├── main.py                # optional: run all three in sequence
├── requirements.txt
├── .env.example
└── data/                  # generated CSVs live here (gitignored)
```
