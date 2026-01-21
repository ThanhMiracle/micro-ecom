# syntax=docker/dockerfile:1.6

# ---- build stage ----
FROM node:20-alpine AS build
WORKDIR /app

# Build-time args (passed from docker-compose)
ARG VITE_AUTH_URL
ARG VITE_PRODUCT_URL
ARG VITE_ORDER_URL

# Vite reads env vars at build time
ENV VITE_AUTH_URL=${VITE_AUTH_URL} \
    VITE_PRODUCT_URL=${VITE_PRODUCT_URL} \
    VITE_ORDER_URL=${VITE_ORDER_URL}

# Install deps with maximum cache efficiency
COPY package.json package-lock.json ./

# Use npm ci for reproducible installs (requires package-lock.json)
RUN --mount=type=cache,target=/root/.npm \
    npm ci

# Copy the rest and build
COPY . .
RUN npm run build


# ---- run stage ----
FROM nginx:1.27-alpine

# SPA routing + caching headers (your nginx.conf should handle)
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Static files only
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
