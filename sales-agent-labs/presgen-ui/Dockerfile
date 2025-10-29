# Dockerfile for PresGen-UI (Next.js Frontend)
# Port: 3000
# Purpose: User interface, assessment workflows, gap analysis dashboard

# Stage 1: Build
FROM node:18-alpine AS builder

LABEL maintainer="ymeirovich@gmail.com"
LABEL service="presgen-ui"
LABEL version="1.0"

WORKDIR /app

# Install dependencies first (layer caching)
COPY package.json package-lock.json ./
# Install ALL dependencies (including dev dependencies needed for build)
RUN npm ci

# Copy source code
COPY . .

# Build application
ARG NEXT_PUBLIC_PRESGEN_ASSESS_URL=/api
ARG NEXT_PUBLIC_PRESGEN_CORE_URL=/core
ENV NEXT_PUBLIC_PRESGEN_ASSESS_URL=${NEXT_PUBLIC_PRESGEN_ASSESS_URL}
ENV NEXT_PUBLIC_PRESGEN_CORE_URL=${NEXT_PUBLIC_PRESGEN_CORE_URL}
ENV NODE_ENV=production

RUN npm run build

# Stage 2: Production runtime
FROM node:18-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy necessary files from builder
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json

# Copy Next.js build output
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000/api/health || exit 1

# Start Next.js server
CMD ["node", "server.js"]
