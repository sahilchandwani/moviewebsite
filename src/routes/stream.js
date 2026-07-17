const express = require('express');
const fs = require('fs');
const path = require('path');
const { requireAuth } = require('../middleware/auth');
const { loadMovie, requireEntitlementApi } = require('../middleware/entitlement');
const { issueStreamToken, verifyStreamToken } = require('../utils/streamToken');
const { streamKeyLimiter } = require('../middleware/security');

const router = express.Router();
const HLS_ROOT = path.join(__dirname, '..', '..', 'media', 'hls');
const KEYS_ROOT = path.join(__dirname, '..', '..', 'media', 'keys');

// Only ever accept simple, non-traversable segment filenames.
const SEGMENT_NAME_RE = /^seg_\d{4,6}\.ts$/;

function noStore(res) {
  res.set('Cache-Control', 'no-store, no-cache, must-revalidate, private');
  res.set('Pragma', 'no-cache');
}

router.get(
  '/:slug/playlist.m3u8',
  requireAuth,
  loadMovie,
  requireEntitlementApi,
  (req, res) => {
    const playlistPath = path.join(HLS_ROOT, req.movie.hls_dir, 'playlist.m3u8');
    if (!fs.existsSync(playlistPath)) return res.status(404).end();

    let manifest = fs.readFileSync(playlistPath, 'utf8');

    const keyToken = issueStreamToken({
      sessionId: req.sessionID,
      userId: req.user.id,
      movieId: req.movie.id,
      purpose: 'key',
      ttlSeconds: 60 * 30, // playback of a single session's manifest can take a while
    });
    const keyUrl = `/stream/${req.movie.slug}/key?t=${encodeURIComponent(keyToken)}`;
    manifest = manifest.replace(/URI="movie\.key"/g, `URI="${keyUrl}"`);

    noStore(res);
    res.set('Content-Type', 'application/vnd.apple.mpegurl');
    res.send(manifest);
  }
);

// Registered before the generic segment route below, since Express matches
// routes in registration order and "/:slug/:segment" would otherwise shadow
// this literal "/:slug/key" path.
router.get(
  '/:slug/key',
  requireAuth,
  streamKeyLimiter,
  loadMovie,
  requireEntitlementApi,
  (req, res) => {
    const valid = verifyStreamToken(req.query.t, {
      sessionId: req.sessionID,
      userId: req.user.id,
      movieId: req.movie.id,
      purpose: 'key',
    });
    if (!valid) return res.status(403).end();

    const keyPath = path.join(KEYS_ROOT, `${req.movie.hls_dir}.key`);
    if (!fs.existsSync(keyPath)) return res.status(404).end();

    noStore(res);
    res.set('Content-Type', 'application/octet-stream');
    fs.createReadStream(keyPath).pipe(res);
  }
);

router.get(
  '/:slug/:segment',
  requireAuth,
  loadMovie,
  requireEntitlementApi,
  (req, res) => {
    const { segment } = req.params;
    if (!SEGMENT_NAME_RE.test(segment)) return res.status(400).end();

    const segmentPath = path.join(HLS_ROOT, req.movie.hls_dir, segment);
    if (!segmentPath.startsWith(path.join(HLS_ROOT, req.movie.hls_dir) + path.sep)) {
      return res.status(400).end();
    }
    if (!fs.existsSync(segmentPath)) return res.status(404).end();

    noStore(res);
    res.set('Content-Type', 'video/mp2t');
    fs.createReadStream(segmentPath).pipe(res);
  }
);

module.exports = router;
