#!/usr/bin/env bash
# Packages a source movie file into AES-128 encrypted HLS for secure in-site
# playback. Never uploads/streams from a third party — output stays local
# under media/hls/<slug>/ and is only ever served through authenticated,
# entitlement-checked routes (see src/routes/stream.js).
#
# Usage: scripts/prepare-video.sh <slug> <path-to-source-video> [poster-time-seconds]
set -euo pipefail

SLUG="${1:?Usage: prepare-video.sh <slug> <source-video-path> [poster-time-seconds]}"
SRC="${2:?Usage: prepare-video.sh <slug> <source-video-path> [poster-time-seconds]}"
POSTER_TIME="${3:-5}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HLS_DIR="$ROOT_DIR/media/hls/$SLUG"
KEYS_DIR="$ROOT_DIR/media/keys"
KEY_FILE="$KEYS_DIR/$SLUG.key"
KEYINFO_FILE="$KEYS_DIR/$SLUG.keyinfo"
POSTER_FILE="$ROOT_DIR/public/images/${SLUG}-poster.jpg"

if [ ! -f "$SRC" ]; then
  echo "Source video not found: $SRC" >&2
  exit 1
fi

command -v ffmpeg >/dev/null 2>&1 || { echo "ffmpeg is required but not installed." >&2; exit 1; }

mkdir -p "$HLS_DIR" "$KEYS_DIR" "$ROOT_DIR/public/images"

# 1. Generate a random 16-byte AES-128 key (kept server-side only, never
#    committed, never served except through the token-gated /stream key route).
openssl rand 16 > "$KEY_FILE"
echo "movie.key" > "$KEYINFO_FILE"
echo "$KEY_FILE" >> "$KEYINFO_FILE"

# 2. Transcode + segment into encrypted HLS.
ffmpeg -y -i "$SRC" \
  -c:v libx264 -preset veryfast -crf 20 \
  -c:a aac -b:a 128k \
  -hls_time 6 \
  -hls_playlist_type vod \
  -hls_key_info_file "$KEYINFO_FILE" \
  -hls_segment_filename "$HLS_DIR/seg_%05d.ts" \
  -master_pl_name "master.m3u8" \
  "$HLS_DIR/playlist.m3u8"

# 3. Grab a poster frame for the movie card.
ffmpeg -y -ss "$POSTER_TIME" -i "$SRC" -update 1 -frames:v 1 -q:v 3 "$POSTER_FILE" || true

echo ""
echo "Done. Encrypted HLS written to: $HLS_DIR"
echo "Key stored at (keep this secret, never commit): $KEY_FILE"
echo "Poster written to: $POSTER_FILE"
echo ""
echo "Now run 'npm run seed' (after updating scripts/seed-movie.js if needed) to register the movie."
