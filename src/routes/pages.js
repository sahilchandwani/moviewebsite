const express = require('express');
const movieModel = require('../models/movie');
const purchaseModel = require('../models/purchase');
const { requireAuth } = require('../middleware/auth');
const { loadMovie, requireEntitlement } = require('../middleware/entitlement');
const router = express.Router();

router.get('/', (req, res) => {
  const movies = movieModel.listPublished();
  const owned = new Set(
    req.user ? movies.filter((m) => purchaseModel.hasEntitlement(req.user.id, m.id)).map((m) => m.id) : []
  );
  res.render('index', { movies, owned });
});

router.get(
  '/watch/:slug',
  requireAuth,
  loadMovie,
  requireEntitlement,
  (req, res) => {
    res.render('watch', { movie: req.movie });
  }
);

router.get('/buy/:slug', requireAuth, loadMovie, (req, res) => {
  if (purchaseModel.hasEntitlement(req.user.id, req.movie.id)) {
    return res.redirect(`/watch/${req.movie.slug}`);
  }
  res.render('buy', { movie: req.movie });
});

module.exports = router;
