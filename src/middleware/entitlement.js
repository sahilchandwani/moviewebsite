const movieModel = require('../models/movie');
const purchaseModel = require('../models/purchase');

// Loads req.movie from :slug and 404s if it doesn't exist / isn't published.
function loadMovie(req, res, next) {
  const movie = movieModel.findBySlug(req.params.slug);
  if (!movie) return res.status(404).render('404');
  req.movie = movie;
  next();
}

// Must run after loadMovie and requireAuth. Renders an HTML upsell page —
// only for page routes (see requireEntitlementApi for media endpoints).
function requireEntitlement(req, res, next) {
  if (!purchaseModel.hasEntitlement(req.user.id, req.movie.id)) {
    return res.status(403).render('locked', { movie: req.movie });
  }
  next();
}

// Same check for the binary/media stream routes, which should never render
// an HTML page in place of a manifest, segment or key response.
function requireEntitlementApi(req, res, next) {
  if (!purchaseModel.hasEntitlement(req.user.id, req.movie.id)) {
    return res.status(403).end();
  }
  next();
}

module.exports = { loadMovie, requireEntitlement, requireEntitlementApi };
