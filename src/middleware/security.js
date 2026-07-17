const crypto = require('crypto');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const env = require('../config/env');

// Per-request nonce so we never need 'unsafe-inline' for scripts/styles.
function cspNonce(req, res, next) {
  res.locals.cspNonce = crypto.randomBytes(16).toString('base64');
  next();
}

const cspDirectives = {
  defaultSrc: ["'self'"],
  imgSrc: ["'self'", 'data:', 'https://*.razorpay.com'],
  connectSrc: ["'self'", 'https://api.razorpay.com', 'https://lumberjack.razorpay.com'],
  frameSrc: ['https://api.razorpay.com', 'https://checkout.razorpay.com'],
  mediaSrc: ["'self'", 'blob:'],
  objectSrc: ["'none'"],
  baseUri: ["'self'"],
  formAction: ["'self'"],
  frameAncestors: ["'none'"],
};
if (env.isProd) cspDirectives.upgradeInsecureRequests = [];

const helmetMiddleware = (req, res, next) =>
  helmet({
    contentSecurityPolicy: {
      directives: {
        ...cspDirectives,
        scriptSrc: ["'self'", `'nonce-${res.locals.cspNonce}'`, 'https://checkout.razorpay.com'],
        styleSrc: ["'self'", `'nonce-${res.locals.cspNonce}'`],
      },
    },
    crossOriginEmbedderPolicy: false,
    crossOriginResourcePolicy: { policy: 'same-origin' },
    hsts: env.isProd ? { maxAge: 31536000, includeSubDomains: true, preload: true } : false,
  })(req, res, next);

function forceHttps(req, res, next) {
  if (!env.isProd) return next();
  const proto = req.headers['x-forwarded-proto'];
  if (proto && proto !== 'https') {
    return res.redirect(301, `https://${req.headers.host}${req.originalUrl}`);
  }
  next();
}

const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 10,
  standardHeaders: true,
  legacyHeaders: false,
  message: 'Too many attempts. Please try again in a few minutes.',
});

const paymentLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 20,
  standardHeaders: true,
  legacyHeaders: false,
  message: 'Too many payment requests. Please try again shortly.',
});

const streamKeyLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 30,
  standardHeaders: true,
  legacyHeaders: false,
});

const globalLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 600,
  standardHeaders: true,
  legacyHeaders: false,
});

module.exports = {
  cspNonce,
  helmetMiddleware,
  forceHttps,
  authLimiter,
  paymentLimiter,
  streamKeyLimiter,
  globalLimiter,
};
