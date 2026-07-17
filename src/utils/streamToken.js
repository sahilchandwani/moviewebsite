const crypto = require('crypto');
const env = require('../config/env');

const DEFAULT_TTL_SECONDS = 90;

function sign(payload) {
  return crypto.createHmac('sha256', env.streamTokenSecret).update(payload).digest('hex');
}

// Short-lived token binding a specific session to a specific movie+resource,
// so decryption keys / segment URLs can't be reused outside the watch session
// or shared as a static link.
function issueStreamToken({ sessionId, userId, movieId, purpose, ttlSeconds = DEFAULT_TTL_SECONDS }) {
  const expires = Math.floor(Date.now() / 1000) + ttlSeconds;
  const payload = `${sessionId}.${userId}.${movieId}.${purpose}.${expires}`;
  const sig = sign(payload);
  return `${expires}.${sig}`;
}

function verifyStreamToken(token, { sessionId, userId, movieId, purpose }) {
  if (!token || typeof token !== 'string') return false;
  const [expiresStr, sig] = token.split('.');
  if (!expiresStr || !sig) return false;
  const expires = parseInt(expiresStr, 10);
  if (!Number.isFinite(expires) || expires < Math.floor(Date.now() / 1000)) return false;

  const payload = `${sessionId}.${userId}.${movieId}.${purpose}.${expires}`;
  const expectedSig = sign(payload);

  const a = Buffer.from(sig, 'hex');
  const b = Buffer.from(expectedSig, 'hex');
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

module.exports = { issueStreamToken, verifyStreamToken };
