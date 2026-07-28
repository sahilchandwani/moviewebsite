#!/usr/bin/env python3
"""Convenience wrapper to run all three outreach stages in sequence.

Prefer running stage1_scrape.py / stage2_generate.py / stage3_output.py
directly when you only need to re-run one stage (e.g. you tweaked the
message-generation prompt and don't want to re-scrape Instagram).
"""
from __future__ import annotations

import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--handles", help="Path to a text file with one Instagram handle per line")
    mode.add_argument("--hashtag", help="One or more hashtags to search, comma-separated (with or without #)")
    parser.add_argument("--limit", type=int, help="Max number of salons to collect (keep this modest)")
    args = parser.parse_args()

    scrape_cmd = [sys.executable, "stage1_scrape.py"]
    if args.handles:
        scrape_cmd += ["--handles", args.handles]
    else:
        scrape_cmd += ["--hashtag", args.hashtag]
    if args.limit:
        scrape_cmd += ["--limit", str(args.limit)]

    for cmd in (scrape_cmd, [sys.executable, "stage2_generate.py"], [sys.executable, "stage3_output.py"]):
        print(f"\n$ {' '.join(cmd)}")
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
