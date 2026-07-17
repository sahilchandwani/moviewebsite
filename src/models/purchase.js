const db = require('../config/db');

function createOrder({ userId, movieId, razorpayOrderId, amountPaise, currency }) {
  const info = db
    .prepare(
      `INSERT INTO purchases (user_id, movie_id, razorpay_order_id, amount_paise, currency, status)
       VALUES (?, ?, ?, ?, ?, 'created')`
    )
    .run(userId, movieId, razorpayOrderId, amountPaise, currency);
  return db.prepare('SELECT * FROM purchases WHERE id = ?').get(info.lastInsertRowid);
}

function findByOrderId(orderId) {
  return db.prepare('SELECT * FROM purchases WHERE razorpay_order_id = ?').get(orderId);
}

function markPaid({ orderId, paymentId }) {
  db.prepare(
    `UPDATE purchases SET status = 'paid', razorpay_payment_id = ?, updated_at = unixepoch()
     WHERE razorpay_order_id = ?`
  ).run(paymentId, orderId);
}

function markFailed(orderId) {
  db.prepare(
    `UPDATE purchases SET status = 'failed', updated_at = unixepoch() WHERE razorpay_order_id = ?`
  ).run(orderId);
}

function hasEntitlement(userId, movieId) {
  const row = db
    .prepare(
      `SELECT 1 FROM purchases WHERE user_id = ? AND movie_id = ? AND status = 'paid' LIMIT 1`
    )
    .get(userId, movieId);
  return !!row;
}

function listForUser(userId) {
  return db
    .prepare(
      `SELECT p.*, m.title, m.slug, m.poster_path FROM purchases p
       JOIN movies m ON m.id = p.movie_id
       WHERE p.user_id = ? ORDER BY p.created_at DESC`
    )
    .all(userId);
}

module.exports = {
  createOrder,
  findByOrderId,
  markPaid,
  markFailed,
  hasEntitlement,
  listForUser,
};
