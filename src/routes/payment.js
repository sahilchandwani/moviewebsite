const express = require('express');
const crypto = require('crypto');
const { getClient } = require('../config/razorpay');
const env = require('../config/env');
const movieModel = require('../models/movie');
const purchaseModel = require('../models/purchase');
const { requireAuth } = require('../middleware/auth');
const { csrfProtection } = require('../middleware/csrf');
const { paymentLimiter } = require('../middleware/security');

const router = express.Router();

router.post('/order/:slug', requireAuth, paymentLimiter, csrfProtection, async (req, res) => {
  const movie = movieModel.findBySlug(req.params.slug);
  if (!movie) return res.status(404).json({ error: 'Movie not found' });

  if (purchaseModel.hasEntitlement(req.user.id, movie.id)) {
    return res.status(400).json({ error: 'You already own this movie.' });
  }

  try {
    const razorpay = getClient();
    const order = await razorpay.orders.create({
      amount: movie.price_paise,
      currency: movie.currency,
      receipt: `movie_${movie.id}_user_${req.user.id}_${Date.now()}`,
      notes: { movieId: String(movie.id), userId: String(req.user.id), slug: movie.slug },
    });

    purchaseModel.createOrder({
      userId: req.user.id,
      movieId: movie.id,
      razorpayOrderId: order.id,
      amountPaise: movie.price_paise,
      currency: movie.currency,
    });

    res.json({
      orderId: order.id,
      amount: order.amount,
      currency: order.currency,
      keyId: env.razorpayKeyId,
      movieTitle: movie.title,
      userName: req.user.name,
      userEmail: req.user.email,
    });
  } catch (err) {
    // The Razorpay SDK rejects with a plain { statusCode, error } object
    // rather than an Error instance, so prefer that shape when present.
    console.error('Razorpay order creation failed:', err.error || err.message || err);
    res.status(502).json({ error: 'Could not start payment. Please try again.' });
  }
});

router.post('/verify', requireAuth, paymentLimiter, csrfProtection, (req, res) => {
  const { razorpay_order_id, razorpay_payment_id, razorpay_signature } = req.body;
  if (!razorpay_order_id || !razorpay_payment_id || !razorpay_signature) {
    return res.status(400).json({ error: 'Missing payment fields.' });
  }

  const purchase = purchaseModel.findByOrderId(razorpay_order_id);
  if (!purchase || purchase.user_id !== req.user.id) {
    return res.status(404).json({ error: 'Order not found.' });
  }

  const expectedSignature = crypto
    .createHmac('sha256', env.razorpayKeySecret)
    .update(`${razorpay_order_id}|${razorpay_payment_id}`)
    .digest('hex');

  const a = Buffer.from(expectedSignature, 'hex');
  const b = Buffer.from(razorpay_signature, 'hex');
  const valid = a.length === b.length && crypto.timingSafeEqual(a, b);

  if (!valid) {
    purchaseModel.markFailed(razorpay_order_id);
    return res.status(400).json({ error: 'Payment verification failed.' });
  }

  purchaseModel.markPaid({ orderId: razorpay_order_id, paymentId: razorpay_payment_id });

  const movie = movieModel.findById(purchase.movie_id);
  res.json({ ok: true, redirect: `/watch/${movie.slug}` });
});

// Server-to-server confirmation from Razorpay. Registered in app.js with a
// raw body parser (needed for signature verification) ahead of the global
// JSON parser, so it is NOT re-mounted on this router.
function handleWebhook(req, res) {
  const signature = req.headers['x-razorpay-signature'];
  if (!signature || !env.razorpayWebhookSecret) return res.status(400).end();

  const expected = crypto
    .createHmac('sha256', env.razorpayWebhookSecret)
    .update(req.body) // raw Buffer
    .digest('hex');

  const a = Buffer.from(expected, 'hex');
  const b = Buffer.from(signature, 'hex');
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) {
    return res.status(400).end();
  }

  let event;
  try {
    event = JSON.parse(req.body.toString('utf8'));
  } catch {
    return res.status(400).end();
  }

  if (event.event === 'payment.captured' || event.event === 'order.paid') {
    const payment = event.payload?.payment?.entity;
    const orderId = payment?.order_id;
    if (orderId) {
      const purchase = purchaseModel.findByOrderId(orderId);
      if (purchase && purchase.status !== 'paid') {
        purchaseModel.markPaid({ orderId, paymentId: payment.id });
      }
    }
  }

  res.status(200).json({ ok: true });
}

module.exports = { router, handleWebhook };
