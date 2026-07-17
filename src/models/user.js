const db = require('../config/db');

const MAX_FAILED_ATTEMPTS = 5;
const LOCK_DURATION_SECONDS = 15 * 60;

function findByEmail(email) {
  return db.prepare('SELECT * FROM users WHERE email = ?').get(email.toLowerCase().trim());
}

function findById(id) {
  return db.prepare('SELECT * FROM users WHERE id = ?').get(id);
}

function create({ email, passwordHash, name }) {
  const stmt = db.prepare(
    'INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)'
  );
  const info = stmt.run(email.toLowerCase().trim(), passwordHash, name.trim());
  return findById(info.lastInsertRowid);
}

function isLocked(user) {
  return !!user.locked_until && user.locked_until > Math.floor(Date.now() / 1000);
}

function registerFailedLogin(user) {
  const failedCount = user.failed_login_count + 1;
  let lockedUntil = user.locked_until;
  if (failedCount >= MAX_FAILED_ATTEMPTS) {
    lockedUntil = Math.floor(Date.now() / 1000) + LOCK_DURATION_SECONDS;
  }
  db.prepare('UPDATE users SET failed_login_count = ?, locked_until = ? WHERE id = ?').run(
    failedCount,
    lockedUntil,
    user.id
  );
}

function clearFailedLogins(userId) {
  db.prepare('UPDATE users SET failed_login_count = 0, locked_until = NULL WHERE id = ?').run(
    userId
  );
}

module.exports = {
  findByEmail,
  findById,
  create,
  isLocked,
  registerFailedLogin,
  clearFailedLogins,
  MAX_FAILED_ATTEMPTS,
  LOCK_DURATION_SECONDS,
};
