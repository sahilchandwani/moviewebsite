#!/usr/bin/env python3
"""
Stage 2: Generate outreach messages for each salon in data/salons.csv via the
Anthropic API.

For each row, generates:
  - instagram_dm            casual, day-1 opener (varied per salon)
  - follow_up_email_subject / follow_up_email_body   day-2 follow-up
  - whatsapp_message        short, low-pressure, day-4 nudge

Writes data/outreach_output.csv with the original columns plus the message
columns and a missing_channels column flagging which touchpoints (phone,
whatsapp, email) are blank for that salon.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import anthropic

import config
from utils import read_csv, write_csv

OUTPUT_FIELDNAMES = [
    "handle", "name", "bio", "website", "phone", "whatsapp", "email",
    "missing_channels",
    "instagram_dm", "follow_up_email_subject", "follow_up_email_body",
    "whatsapp_message",
]

SAMPLE_DM = (
    "Hey! Quick one for you — I work with UAE perfume manufacturers and had an idea "
    "for [Salon]. Your clients are already sitting with you for a good while each visit "
    "— that's honestly one of the best upsell windows in retail. A branded, signature "
    "perfume with your salon's name on it turns that time into extra revenue, keeps "
    "clients loyal to you specifically, and it's a strong margin product. We can do this "
    "white-label, UAE-made, low/no MOQ, good pricing and flexible terms — easy to test "
    "without big upfront risk. Want to hop on a quick call this week? I can bring samples "
    "so you can see how it'd work for your salon."
)

SYSTEM_PROMPT = f"""You are a copywriter helping a UAE-based white-label perfume \
manufacturer write outreach messages to hair and beauty salons. You will be given \
one salon's public Instagram profile info and must write three outreach messages \
for a sequence: an Instagram DM (day 1), a follow-up email (day 2), and a WhatsApp \
message (day 4).

The core pitch, which must come through in all three messages: the salon's clients \
already sit in the chair for a long time per visit -- a great upsell window. A \
branded, signature perfume with the salon's own name on it turns that time into \
extra revenue, builds client loyalty to that specific salon, and is a strong-margin \
product. It's offered white-label, UAE-made, with low/no MOQ, good pricing, and \
flexible terms -- easy to test without big upfront risk.

Style guide per message:
1. instagram_dm: Casual tone, matching the style of this sample (vary the opening \
line so it doesn't read like a template -- personalize it using the salon's name \
and, if useful, a detail from its bio):
\"\"\"{SAMPLE_DM}\"\"\"
2. follow_up_email: Slightly more detailed and formal than the DM. Assumes the DM \
was sent 1 day earlier with no reply. Return both a subject line and a body.
3. whatsapp_message: Short, casual, low-pressure. Assumes both the DM and the \
email were already sent with no reply.

Respond with ONLY a single JSON object, no markdown fences, no commentary, with \
exactly these keys: "instagram_dm" (string), "follow_up_email_subject" (string), \
"follow_up_email_body" (string), "whatsapp_message" (string)."""


def build_user_prompt(row: dict) -> str:
    name = row.get("name") or row.get("handle")
    bio = row.get("bio") or "(no bio available)"
    return (
        f"Salon Instagram handle: @{row.get('handle')}\n"
        f"Salon / display name: {name}\n"
        f"Bio: {bio}\n\n"
        "Write the three outreach messages now, as a single JSON object."
    )


def missing_channels(row: dict) -> str:
    missing = [c for c in ("phone", "whatsapp", "email") if not row.get(c)]
    return ",".join(missing)


def parse_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.lower().startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def generate_messages(client: anthropic.Anthropic, row: dict) -> dict:
    last_error = None
    for attempt in range(2):
        try:
            response = client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=1500,
                temperature=0.9,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": build_user_prompt(row)}],
            )
        except anthropic.RateLimitError:
            print(f"  Rate limited on @{row.get('handle')}, backing off...")
            time.sleep(10 * (attempt + 1))
            continue
        except anthropic.APIStatusError as e:
            last_error = f"API error {e.status_code}: {e.message}"
            break
        except anthropic.APIConnectionError as e:
            last_error = f"connection error: {e}"
            time.sleep(5)
            continue

        if response.stop_reason == "refusal":
            last_error = "model declined to generate a response"
            break

        text = "".join(b.text for b in response.content if b.type == "text")
        try:
            data = parse_json_response(text)
            return {
                "instagram_dm": data.get("instagram_dm", ""),
                "follow_up_email_subject": data.get("follow_up_email_subject", ""),
                "follow_up_email_body": data.get("follow_up_email_body", ""),
                "whatsapp_message": data.get("whatsapp_message", ""),
            }
        except (json.JSONDecodeError, IndexError) as e:
            last_error = f"could not parse model output as JSON: {e}"
            continue

    print(f"  WARNING: failed to generate messages for @{row.get('handle')}: {last_error}", file=sys.stderr)
    return {
        "instagram_dm": "",
        "follow_up_email_subject": "",
        "follow_up_email_body": "",
        "whatsapp_message": "",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="infile", default=str(config.SALONS_CSV))
    parser.add_argument("--out", dest="outfile", default=str(config.OUTREACH_CSV))
    args = parser.parse_args()

    if not config.ANTHROPIC_API_KEY:
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in.")

    rows = read_csv(args.infile)
    if not rows:
        sys.exit(f"No rows found in {args.infile} -- run stage1_scrape.py first.")

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    output_rows = []
    for i, row in enumerate(rows, start=1):
        print(f"[{i}/{len(rows)}] Generating messages for @{row.get('handle')}...")
        messages = generate_messages(client, row)
        output_rows.append({**row, "missing_channels": missing_channels(row), **messages})
        time.sleep(config.CLAUDE_REQUEST_DELAY_SECONDS)

    write_csv(args.outfile, output_rows, OUTPUT_FIELDNAMES)
    print(f"Wrote {len(output_rows)} row(s) to {args.outfile}")

    failed = [r["handle"] for r in output_rows if not r["instagram_dm"]]
    if failed:
        print(f"Note: message generation failed for: {', '.join(failed)} (see warnings above)")


if __name__ == "__main__":
    main()
