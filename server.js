const env = require('./src/config/env');
const app = require('./src/app');

app.listen(env.port, () => {
  console.log(`S4 Entertainments running on ${env.baseUrl} (${env.nodeEnv})`);
});
