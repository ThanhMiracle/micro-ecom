#!/bin/sh
set -eu

# Default values (optional)
: "${VITE_AUTH_URL:=}"
: "${VITE_PRODUCT_URL:=}"
: "${VITE_ORDER_URL:=}"

# Generate runtime config JS served by nginx
cat > /usr/share/nginx/html/env.js <<EOF
window.__ENV__ = {
  VITE_AUTH_URL: "${VITE_AUTH_URL}",
  VITE_PRODUCT_URL: "${VITE_PRODUCT_URL}",
  VITE_ORDER_URL: "${VITE_ORDER_URL}"
};
EOF

# Optional: prevent caching of env.js (best practice)
# You can also do this in nginx.conf headers.
# (No-op here; just note.)

exec "$@"
