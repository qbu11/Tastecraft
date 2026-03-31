# ==============================================================================
# Tastecraft 品匠 — Frontend Dockerfile (React + Vite + nginx)
# Build context: frontend/ directory
# ==============================================================================

# --------------- Stage 1: Build React app ---------------
FROM node:20-alpine AS builder

WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy dependency files first (cache-friendly)
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source and build
COPY . ./
RUN pnpm build

# --------------- Stage 2: Serve with nginx ---------------
FROM nginx:alpine AS runtime

RUN rm /etc/nginx/conf.d/default.conf

# Use template with env var substitution for Railway dynamic port
COPY <<'NGINX_TMPL' /etc/nginx/templates/tastecraft.conf.template
server {
    listen ${PORT};
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript image/svg+xml;
    gzip_min_length 1000;

    # Static assets with long cache
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Dynamic DNS resolution — avoids nginx startup failure if backend not ready
    resolver 8.8.8.8 valid=30s ipv6=off;
    set $backend_upstream http://${BACKEND_HOST}:${BACKEND_PORT};

    # Proxy API calls to backend
    location /api/ {
        proxy_pass $backend_upstream;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Proxy WebSocket
    location /ws/ {
        proxy_pass $backend_upstream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
NGINX_TMPL

# Copy built files from builder
COPY --from=builder /app/dist/ /usr/share/nginx/html/

# Default env vars (Railway overrides PORT; set BACKEND_HOST in Railway dashboard)
ENV PORT=3000 \
    BACKEND_HOST=backend.railway.internal \
    BACKEND_PORT=8000

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:${PORT}/ || exit 1

# envsubst replaces ${PORT}, ${BACKEND_HOST}, ${BACKEND_PORT} at startup
# $uri and $host are nginx variables — must NOT be substituted
CMD ["/bin/sh", "-c", "envsubst '${PORT} ${BACKEND_HOST} ${BACKEND_PORT}' < /etc/nginx/templates/tastecraft.conf.template > /etc/nginx/conf.d/tastecraft.conf && nginx -g 'daemon off;'"]
