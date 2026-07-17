const Razorpay = require('razorpay');
const env = require('../config/env');

let client = null;

function getClient() {
  if (!env.razorpayKeyId || !env.razorpayKeySecret) {
    throw new Error(
      'Razorpay is not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env'
    );
  }
  if (!client) {
    client = new Razorpay({ key_id: env.razorpayKeyId, key_secret: env.razorpayKeySecret });
  }
  return client;
}

module.exports = { getClient };
