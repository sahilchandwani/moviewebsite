// Inserts/updates the flagship movie's metadata row in the database.
// Run with: npm run seed
const env = require('../src/config/env');
const movie = require('../src/models/movie');

const record = movie.upsert({
  slug: 'dil-jo-safar',
  title: 'Dil Jo Safar',
  tagline: 'A journey of the heart, told in Sindhi.',
  description:
    "S4 Entertainments' flagship feature film — a story of family, love and " +
    'the Sindhi diaspora finding its way home. Watch the full movie exclusively ' +
    'on this site after unlocking it below.',
  poster_path: '/public/images/dil-jo-safar-poster.jpg',
  hls_dir: 'dil-jo-safar',
  duration_minutes: 128,
  release_year: 2026,
  price_paise: env.moviePricePaise,
  currency: env.movieCurrency,
  is_published: 1,
});

console.log('Seeded movie:', record);
