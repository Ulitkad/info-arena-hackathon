# syntax=docker/dockerfile:1

FROM node:24-alpine AS dependencies
WORKDIR /app

COPY --link frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm,sharing=locked \
    npm ci

FROM dependencies AS build
COPY --link frontend/ ./
RUN npm run build

FROM nginx:stable-alpine
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
