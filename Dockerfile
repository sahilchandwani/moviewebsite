# Builds a ready-to-run image for hosting platforms like Render/Railway/Fly.
# ffmpeg is needed at build time to package the sample movie into encrypted
# HLS (see scripts/prepare-video.sh) so the site works immediately on a
# fresh deploy, with no terminal access required from whoever is deploying it.
FROM node:20-bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg openssl bash \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY . .

# Bake in a synthetic sample movie (color-bar test pattern, ~20s) so the
# full paywall + encrypted playback pipeline is provably working the moment
# this deploys. Swap in the real film later with the same script, then
# rebuild/redeploy — see README.md.
RUN ffmpeg -f lavfi -i "testsrc=duration=20:size=1280x720:rate=30" \
      -f lavfi -i "sine=frequency=440:duration=20" \
      -c:v libx264 -c:a aac -shortest media/source/sample.mp4 \
 && bash scripts/prepare-video.sh dil-jo-safar media/source/sample.mp4 10 \
 && node scripts/seed-movie.js

# Set after the RUN step above so that step still uses harmless local
# defaults for secrets it doesn't actually need (see src/config/env.js) —
# the real secrets are injected as environment variables at runtime by the
# hosting platform, not baked into the image.
ENV NODE_ENV=production

EXPOSE 3000

CMD ["node", "server.js"]
