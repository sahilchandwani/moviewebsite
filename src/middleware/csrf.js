const { doubleCsrf } = require('csrf-csrf');
const env = require('../config/env');

const { doubleCsrfProtection, generateToken } = doubleCsrf({
  getSecret: () => env.csrfSecret,
  getSessionIdentifier: (req) => req.sessionID || '',
  cookieName: env.isProd ? '__Host-s4.csrf' : 's4.csrf',
  cookieOptions: {
    sameSite: 'lax',
    path: '/',
    secure: env.isProd,
    httpOnly: true,
  },
  getTokenFromRequest: (req) =>
    (req.body && req.body._csrf) || req.headers['x-csrf-token'],
});

// The CSRF token is bound to the session ID (see getSessionIdentifier above),
// but express-session only persists a session — and hands out a stable ID —
// once something touches req.session. Without this, an anonymous visitor's
// sessionID would silently change between the page load that mints a CSRF
// token and the form POST that submits it, so every logged-out form
// (login, register) would fail CSRF validation. Touching the session here,
// before the token is generated, forces it to be saved immediately.
function ensureSession(req, res, next) {
  if (req.session && !req.session.touchedAt) {
    req.session.touchedAt = Date.now();
  }
  next();
}

// Makes a token available to every EJS view as `csrfToken`. Reuses the
// existing cookie's token when it's still valid for this session, but must
// NOT throw when it isn't (e.g. right after login regenerates the session
// ID, which invalidates the old CSRF cookie's session binding) — this runs
// on every request, including plain page loads, so it just mints a fresh
// token silently in that case rather than erroring the request out.
function exposeCsrfToken(req, res, next) {
  res.locals.csrfToken = generateToken(req, res, false, false);
  next();
}

module.exports = { csrfProtection: doubleCsrfProtection, exposeCsrfToken, ensureSession };
