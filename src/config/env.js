const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '..', '.env') });

function required(name, fallbackDev) {
  const value = process.env[name];
  if (value) return value;
  if (process.env.NODE_ENV !== 'production' && fallbackDev !== undefined) return fallbackDev;
  throw new Error(`Missing required environment variable: ${name}`);
}

module.exports = {
  nodeEnv: process.env.NODE_ENV || 'development',
  isProd: process.env.NODE_ENV === 'production',
  port: parseInt(process.env.PORT, 10) || 3000,
  baseUrl: process.env.BASE_URL || 'http://localhost:3000',

  sessionSecret: required('SESSION_SECRET', 'dev-only-insecure-session-secret'),
  csrfSecret: required('CSRF_SECRET', 'dev-only-insecure-csrf-secret'),
  streamTokenSecret: required('STREAM_TOKEN_SECRET', 'dev-only-insecure-stream-secret'),

  razorpayKeyId: process.env.RAZORPAY_KEY_ID || '',
  razorpayKeySecret: process.env.RAZORPAY_KEY_SECRET || '',
  razorpayWebhookSecret: process.env.RAZORPAY_WEBHOOK_SECRET || '',

  moviePricePaise: parseInt(process.env.MOVIE_PRICE_PAISE, 10) || 19900,
  movieCurrency: process.env.MOVIE_CURRENCY || 'INR',
};
