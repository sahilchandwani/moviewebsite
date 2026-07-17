# S4 Entertainments

A website for **S4 Entertainments**, a Sindhi film production house — showcasing
films behind a paywall, with the movie itself played back entirely on this site
(never embedded from or streamed via a third-party video host).

## Stack

- **Node.js + Express + EJS** — server-rendered pages, sessions kept server-side.
- **SQLite** (`better-sqlite3`) — users, movies, purchases. No external DB to run.
- **Razorpay** — paywall/checkout (order creation + signature-verified payment capture).
- **HLS + AES-128 encryption** (via `ffmpeg`) — the movie is packaged into encrypted
  streaming segments. Only an authenticated session that has actually paid for the
  film can fetch the manifest, the segments, or the decryption key, and the key is
  handed out through a short-lived, single-purpose signed token — never a static URL.
- **hls.js** (vendored, no CDN) for in-browser playback; Safari uses its native HLS support.

## Security measures baked in

- Passwords hashed with bcrypt (12 rounds); timing-safe login (dummy hash compare
  on unknown emails to resist user enumeration); account lockout after 5 failed
  attempts (15 min).
- Sessions are httpOnly, `SameSite=Lax` cookies, regenerated on login (fixes
  session fixation), stored server-side in SQLite.
- CSRF protection (double-submit cookie, `csrf-csrf`) on every state-changing
  route (register, login, logout, payment, etc).
- `helmet` with a strict, nonce-based Content-Security-Policy — no inline
  scripts/styles anywhere in the app, so there's no `unsafe-inline` in the CSP.
  The only third-party origin allowed at all is Razorpay's checkout.
- Rate limiting on auth and payment endpoints; a general limiter on everything else.
- Razorpay payments are verified server-side via HMAC signature (both the
  client-side redirect callback and an independent webhook as a durable fallback)
  before an entitlement is ever granted — the client never dictates "I paid."
- The movie's AES-128 key and HLS segments live outside any statically-served
  directory. Every request for the manifest, a segment, or the key re-checks
  the session is logged in **and** has a paid entitlement for that exact movie.
  The key endpoint additionally requires a signed, ~30-minute token bound to
  the specific session + movie, so key URLs can't be shared or replayed from
  another account. All stream responses are `Cache-Control: no-store`.
- The player page shows a small watermark of the viewer's account email over
  the video and disables the right-click menu / native download affordances,
  as a deterrent (not a guarantee) against casual redistribution.

No system is 100% piracy-proof against someone determined to screen-record —
this setup is meant to stop casual link-sharing/downloading, not nation-state
level DRM.

## Getting started

```bash
npm install
cp .env.example .env    # then fill in real secrets (see below)
```

Generate secrets for `.env`:

```bash
openssl rand -hex 32   # run 3x for SESSION_SECRET, CSRF_SECRET, STREAM_TOKEN_SECRET
```

Get Razorpay test keys from https://dashboard.razorpay.com/app/keys and put them
in `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET`. For the webhook fallback, add a
webhook in the Razorpay dashboard pointing at `https://<your-domain>/payment/webhook`
subscribed to `payment.captured`, and put its secret in `RAZORPAY_WEBHOOK_SECRET`.

### Adding your real movie

The repo ships with a short synthetic test clip already packaged end-to-end (so
the paywall + playback pipeline is provable out of the box), registered as the
placeholder movie "Dil Jo Safar". To replace it with your real film:

```bash
# 1. Package the movie into encrypted HLS (requires ffmpeg)
bash scripts/prepare-video.sh dil-jo-safar /path/to/your-movie.mp4 30
#                              ^slug        ^source file           ^poster frame at 30s

# 2. Edit scripts/seed-movie.js with the real title/description/price/etc,
#    then register it in the database
npm run seed
```

To add a second film, pick a new slug and repeat both steps with a new `movie.upsert(...)`
block in `scripts/seed-movie.js` (or a small script of your own using `src/models/movie.js`).

The original source file and the HLS output/keys are intentionally **not** committed
(see `.gitignore`) — they're regenerated locally/on the server from
`scripts/prepare-video.sh`, and the AES key must never leave the server.

### Run it

```bash
npm start          # production-style start
npm run dev         # auto-restarts on file changes
```

Visit http://localhost:3000.

## Project layout

```
server.js              Entry point
src/
  app.js                Express app wiring (middleware order matters — see comments)
  config/                env, db, session, razorpay
  middleware/             auth, csrf, entitlement, security (helmet/rate limits)
  models/                 users, movies, purchases (SQLite queries)
  routes/                 pages, auth, payment, stream
  views/                  EJS templates
public/                 Static assets (css/js/images) — served at /public
media/
  source/                 Your original movie files (gitignored)
  hls/                    Encrypted HLS output per movie (gitignored)
  keys/                   AES-128 keys, one per movie (gitignored — never commit these)
scripts/
  prepare-video.sh         ffmpeg packaging pipeline
  seed-movie.js             registers a movie's metadata in the DB
```

## Deploying

- Run behind HTTPS (a reverse proxy like nginx/Caddy, or your host's TLS
  termination) — `NODE_ENV=production` turns on HSTS, secure cookies, and an
  HTTP→HTTPS redirect based on `X-Forwarded-Proto`, so `app.set('trust proxy', 1)`
  assumes you're behind exactly one trusted proxy hop.
- Set every secret in `.env` to a freshly generated value in production —
  don't reuse the dev placeholders.
- The SQLite file at `data/app.sqlite` is your whole database; back it up.
