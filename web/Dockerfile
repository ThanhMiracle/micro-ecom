# ---- build stage ----
FROM node:20-alpine AS build
WORKDIR /app

# 🔹 Accept build-time args from docker-compose
ARG VITE_AUTH_URL
ARG VITE_PRODUCT_URL
ARG VITE_ORDER_URL

# 🔹 Expose them as env vars for Vite build
ENV VITE_AUTH_URL=$VITE_AUTH_URL
ENV VITE_PRODUCT_URL=$VITE_PRODUCT_URL
ENV VITE_ORDER_URL=$VITE_ORDER_URL

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

# ---- run stage ----
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html

# Optional but recommended: SPA routing support
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
