const db = require('../config/db');

function findBySlug(slug) {
  return db
    .prepare('SELECT * FROM movies WHERE slug = ? AND is_published = 1')
    .get(slug);
}

function findById(id) {
  return db.prepare('SELECT * FROM movies WHERE id = ?').get(id);
}

function listPublished() {
  return db
    .prepare('SELECT * FROM movies WHERE is_published = 1 ORDER BY created_at DESC')
    .all();
}

function upsert(movie) {
  const existing = findBySlug(movie.slug);
  if (existing) {
    db.prepare(
      `UPDATE movies SET title=?, tagline=?, description=?, poster_path=?, hls_dir=?,
       duration_minutes=?, release_year=?, price_paise=?, currency=?, is_published=?
       WHERE slug=?`
    ).run(
      movie.title,
      movie.tagline,
      movie.description,
      movie.poster_path,
      movie.hls_dir,
      movie.duration_minutes,
      movie.release_year,
      movie.price_paise,
      movie.currency,
      movie.is_published ?? 1,
      movie.slug
    );
    return findBySlug(movie.slug);
  }
  const info = db
    .prepare(
      `INSERT INTO movies
       (slug, title, tagline, description, poster_path, hls_dir, duration_minutes,
        release_year, price_paise, currency, is_published)
       VALUES (@slug, @title, @tagline, @description, @poster_path, @hls_dir,
        @duration_minutes, @release_year, @price_paise, @currency, @is_published)`
    )
    .run({ is_published: 1, ...movie });
  return findById(info.lastInsertRowid);
}

module.exports = { findBySlug, findById, listPublished, upsert };
