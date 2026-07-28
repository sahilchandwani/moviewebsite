#!/usr/bin/env python3
"""
Stage 3: Turn data/outreach_output.csv into an actionable day-by-day plan.

- Never sends or auto-posts anything to Instagram or WhatsApp -- there's no
  API for that here, and there is deliberately no code in this project that
  mimics automated bulk messaging on Instagram. Those two channels go out
  manually, from your own accounts.
- If Gmail OAuth credentials are configured (GMAIL_CREDENTIALS_PATH /
  GMAIL_TOKEN_PATH env vars), creates a Gmail DRAFT -- never sent
  automatically -- for each salon's follow-up email, addressed to the
  salon's email if one was found. NOTE: the Gmail API has no "send later" /
  schedule field on drafts, so this only creates the draft in your Drafts
  folder; you (or your own reminder) still have to send it on day 2.
- Otherwise, just prints a CLI checklist and leaves everything in the CSV
  for you to work from manually.
"""
from __future__ import annotations

import argparse
import base64
import os
import sys
from email.mime.text import MIMEText

import config
from utils import read_csv


def try_gmail_service():
    """Return an authenticated Gmail API service, or None if not configured."""
    if not (config.GMAIL_CREDENTIALS_PATH and config.GMAIL_TOKEN_PATH):
        return None
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        print(
            "Gmail credentials are configured but the Gmail API libraries aren't "
            "installed. Run: pip install -r requirements.txt",
            file=sys.stderr,
        )
        return None

    scopes = ["https://www.googleapis.com/auth/gmail.compose"]
    token_path = config.GMAIL_TOKEN_PATH

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(config.GMAIL_CREDENTIALS_PATH):
                print(f"GMAIL_CREDENTIALS_PATH ({config.GMAIL_CREDENTIALS_PATH}) not found.", file=sys.stderr)
                return None
            flow = InstalledAppFlow.from_client_secrets_file(config.GMAIL_CREDENTIALS_PATH, scopes)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def create_gmail_draft(service, to_email: str, subject: str, body: str) -> str | None:
    message = MIMEText(body)
    message["to"] = to_email
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    try:
        draft = service.users().drafts().create(
            userId=config.GMAIL_SENDER, body={"message": {"raw": raw}}
        ).execute()
        return draft.get("id")
    except Exception as e:  # Gmail API surface raises HttpError and friends
        print(f"  Failed to create Gmail draft for {to_email}: {e}", file=sys.stderr)
        return None


def print_summary(rows: list[dict], drafted_count: int) -> None:
    print("\n=== UAE Salon Outreach — Day-by-Day Checklist ===\n")

    print("Day 1 — send these Instagram DMs manually:")
    for r in rows:
        if r.get("instagram_dm"):
            print(f"  @{r['handle']}: {r['instagram_dm'][:90]}...")
    print()

    print("Day 2 — follow-up emails:")
    if drafted_count:
        print(f"  {drafted_count} draft(s) created in Gmail — review and send from your Drafts folder.")
    else:
        for r in rows:
            if r.get("follow_up_email_subject"):
                to = r.get("email") or "(no email found — send another way or skip)"
                print(f"  @{r['handle']} -> {to}")
                print(f"    Subject: {r['follow_up_email_subject']}")
    print()

    print("Day 4 — send these WhatsApp messages manually:")
    for r in rows:
        if r.get("whatsapp_message"):
            to = r.get("whatsapp") or "(no WhatsApp number found)"
            print(f"  @{r['handle']} -> {to}: {r['whatsapp_message'][:90]}...")
    print()

    flagged = [r for r in rows if r.get("missing_channels")]
    if flagged:
        print("Rows with missing touchpoints (won't work as written):")
        for r in flagged:
            print(f"  @{r['handle']}: missing {r['missing_channels']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="infile", default=str(config.OUTREACH_CSV))
    args = parser.parse_args()

    rows = read_csv(args.infile)
    if not rows:
        sys.exit(f"No rows found in {args.infile} -- run stage2_generate.py first.")

    drafted_count = 0
    service = try_gmail_service()
    if service:
        print("Gmail credentials found — creating drafts for follow-up emails...")
        for r in rows:
            if r.get("email") and r.get("follow_up_email_subject"):
                draft_id = create_gmail_draft(
                    service, r["email"], r["follow_up_email_subject"], r["follow_up_email_body"]
                )
                if draft_id:
                    drafted_count += 1
    else:
        print("No Gmail credentials configured — skipping draft creation (see README.md).")

    print_summary(rows, drafted_count)


if __name__ == "__main__":
    main()
