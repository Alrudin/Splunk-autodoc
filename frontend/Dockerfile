# Stage 1: Builder
FROM node:20-alpine AS builder

WORKDIR /build

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

# Copy source files
COPY tsconfig.json tsconfig.app.json tsconfig.node.json ./
COPY index.html ./
COPY vite.config.ts* ./
COPY postcss.config.js tailwind.config.js ./
COPY public ./public
COPY src ./src

# Build application
RUN npm run build

# Stage 2: Runtime
FROM nginx:alpine

# Remove default nginx content
RUN rm -rf /usr/share/nginx/html/*

# Copy built static files
COPY --from=builder /build/dist /usr/share/nginx/html

# Create entrypoint script to inject runtime config
RUN cat > /docker-entrypoint.sh <<'EOF'
#!/bin/sh
set -e

# Generate runtime config from environment variables
cat > /usr/share/nginx/html/config.js <<CONFIGEOF
window.APP_CONFIG = {
  API_BASE_URL: "${API_BASE_URL:-http://localhost:8000/api/v1}"
};
CONFIGEOF

echo "Generated config.js with API_BASE_URL=${API_BASE_URL:-http://localhost:8000/api/v1}"

# Execute the CMD
exec "$@"
EOF

RUN chmod +x /docker-entrypoint.sh

# Create custom nginx configuration
RUN cat > /etc/nginx/conf.d/default.conf <<'EOF'
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Allow large file uploads (3GB per spec section 13)
    client_max_body_size 3G;

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://api:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Increase timeouts for file uploads
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
        send_timeout 600;
    }

    # SPA routing - serve index.html for all routes
    location / {
        try_files $uri $uri/ /index.html;
        # No cache for index.html
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }

    # Cache static assets with hash in filename
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Expose HTTP port
EXPOSE 80

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:80/ || exit 1

# Set entrypoint and start nginx
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
