const express = require('express');
const crypto = require('crypto');
const bcrypt = require('bcryptjs');
const { body, validationResult } = require('express-validator');
const userModel = require('../models/user');
const { requireGuest, requireAuth } = require('../middleware/auth');
const { csrfProtection } = require('../middleware/csrf');
const { authLimiter } = require('../middleware/security');
const purchaseModel = require('../models/purchase');

const router = express.Router();

// A valid-format bcrypt hash with no matching plaintext, used to equalize
// response timing when an email lookup misses (prevents user enumeration).
const DUMMY_HASH = bcrypt.hashSync(crypto.randomBytes(24).toString('hex'), 12);

const registerValidators = [
  body('name').trim().isLength({ min: 2, max: 80 }).withMessage('Please enter your name.'),
  body('email').trim().isEmail().withMessage('Please enter a valid email.').normalizeEmail(),
  body('password')
    .isLength({ min: 10 })
    .withMessage('Password must be at least 10 characters long.')
    .matches(/[a-z]/)
    .withMessage('Password must include a lowercase letter.')
    .matches(/[A-Z]/)
    .withMessage('Password must include an uppercase letter.')
    .matches(/[0-9]/)
    .withMessage('Password must include a number.'),
  body('confirmPassword').custom((value, { req }) => {
    if (value !== req.body.password) throw new Error('Passwords do not match.');
    return true;
  }),
];

router.get('/register', requireGuest, (req, res) => {
  res.render('register', { errors: [], values: {} });
});

router.post(
  '/register',
  requireGuest,
  authLimiter,
  csrfProtection,
  registerValidators,
  async (req, res) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).render('register', {
        errors: errors.array().map((e) => e.msg),
        values: { name: req.body.name, email: req.body.email },
      });
    }

    const { name, email, password } = req.body;
    if (userModel.findByEmail(email)) {
      return res.status(400).render('register', {
        errors: ['An account with that email already exists.'],
        values: { name, email },
      });
    }

    const passwordHash = await bcrypt.hash(password, 12);
    const user = userModel.create({ email, passwordHash, name });

    req.session.regenerate((err) => {
      if (err) throw err;
      req.session.userId = user.id;
      res.redirect('/account');
    });
  }
);

router.get('/login', requireGuest, (req, res) => {
  res.render('login', { error: null, values: {} });
});

router.post('/login', requireGuest, authLimiter, csrfProtection, async (req, res) => {
  const email = (req.body.email || '').trim();
  const password = req.body.password || '';
  const genericError = 'Incorrect email or password.';

  const user = userModel.findByEmail(email);
  if (!user) {
    // Still hash something to keep timing similar whether or not the account exists.
    await bcrypt.compare(password, DUMMY_HASH);
    return res.status(400).render('login', { error: genericError, values: { email } });
  }

  if (userModel.isLocked(user)) {
    return res
      .status(429)
      .render('login', { error: 'Too many failed attempts. Try again later.', values: { email } });
  }

  const valid = await bcrypt.compare(password, user.password_hash);
  if (!valid) {
    userModel.registerFailedLogin(user);
    return res.status(400).render('login', { error: genericError, values: { email } });
  }

  userModel.clearFailedLogins(user.id);

  req.session.regenerate((err) => {
    if (err) throw err;
    req.session.userId = user.id;
    const returnTo = req.session.returnTo;
    delete req.session.returnTo;
    res.redirect(returnTo || '/account');
  });
});

router.post('/logout', csrfProtection, (req, res) => {
  req.session.destroy(() => {
    res.clearCookie('s4.sid');
    res.redirect('/');
  });
});

router.get('/account', requireAuth, (req, res) => {
  const purchases = purchaseModel.listForUser(req.user.id);
  res.render('account', { purchases });
});

module.exports = router;
