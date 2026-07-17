const userModel = require('../models/user');

// Loads the logged-in user (if any) onto req/res.locals for every request.
function attachUser(req, res, next) {
  if (req.session && req.session.userId) {
    const user = userModel.findById(req.session.userId);
    if (user) {
      req.user = user;
      res.locals.user = { id: user.id, name: user.name, email: user.email };
      return next();
    }
  }
  req.user = null;
  res.locals.user = null;
  next();
}

function requireAuth(req, res, next) {
  if (!req.user) {
    req.session.returnTo = req.originalUrl;
    return res.redirect('/login');
  }
  next();
}

function requireGuest(req, res, next) {
  if (req.user) return res.redirect('/account');
  next();
}

module.exports = { attachUser, requireAuth, requireGuest };
