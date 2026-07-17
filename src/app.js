const path = require('path');
const express = require('express');
const compression = require('compression');
const morgan = require('morgan');
const cookieParser = require('cookie-parser');

const env = require('./config/env');
const sessionMiddleware = require('./config/session');
const { attachUser } = require('./middleware/auth');
const { exposeCsrfToken, ensureSession } = require('./middleware/csrf');
const {
  cspNonce,
  helmetMiddleware,
  forceHttps,
  globalLimiter,
} = require('./middleware/security');

const pagesRouter = require('./routes/pages');
const authRouter = require('./routes/auth');
const streamRouter = require('./routes/stream');
const { router: paymentRouter, handleWebhook } = require('./routes/payment');

const app = express();

app.set('trust proxy', 1);
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

app.use(compression());
if (env.nodeEnv !== 'test') {
  app.use(morgan(env.isProd ? 'combined' : 'dev'));
}

app.use(cspNonce);
app.use(helmetMiddleware);
app.use(forceHttps);

// Razorpay webhook needs the raw request body for signature verification,
// so it is registered ahead of the global JSON body parser below.
app.post('/payment/webhook', express.raw({ type: 'application/json' }), handleWebhook);

app.use(express.json({ limit: '20kb' }));
app.use(express.urlencoded({ extended: false, limit: '20kb' }));
app.use(cookieParser());

app.use(
  '/public',
  express.static(path.join(__dirname, '..', 'public'), {
    maxAge: env.isProd ? '7d' : 0,
    setHeaders: (res) => res.set('X-Content-Type-Options', 'nosniff'),
  })
);

app.use(globalLimiter);
app.use(sessionMiddleware);
app.use(ensureSession);
app.use(attachUser);
app.use(exposeCsrfToken);

app.use('/', pagesRouter);
app.use('/', authRouter);
app.use('/payment', paymentRouter);
app.use('/stream', streamRouter);

app.use((req, res) => {
  res.status(404).render('404');
});

// eslint-disable-next-line no-unused-vars
app.use((err, req, res, next) => {
  if (err && err.code === 'EBADCSRFTOKEN') {
    return res.status(403).render('error', {
      message: 'Your session expired or the form was tampered with. Please try again.',
    });
  }
  console.error(err);
  res.status(500).render('error', { message: 'Something went wrong. Please try again.' });
});

module.exports = app;
