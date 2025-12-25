# ============================================
# PHRONAI React Frontend - Production Dockerfile
# ============================================
# Optimized for Railway deployment

FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source
COPY . .

# Build arguments for environment variables
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_API_WS_URL

# Set environment for build
ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL
ENV VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY
ENV VITE_API_WS_URL=$VITE_API_WS_URL

# Build
RUN npm run build

# ============================================
# Production Stage - Nginx
# ============================================
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port (Railway sets PORT env var)
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
