FROM node:20-alpine

WORKDIR /app

COPY optic-platform/package.json ./package.json
COPY optic-platform/server.mjs ./server.mjs
COPY optic-platform/public ./public
COPY optic-platform/src ./src

EXPOSE 4314

CMD ["node", "server.mjs"]