FROM node:20-alpine AS builder

WORKDIR /app

# Copy entire repo (needed for /db/seed/entries.json and apps/site)
COPY . .

# Install dependencies from apps/site
RUN npm ci --prefix apps/site

# Build static site from apps/site
RUN npm run build --prefix apps/site

# Runtime: serve static files with minimal HTTP server
FROM node:20-alpine

WORKDIR /app

# Install serve to run the static site (lightweight alternative to full Node.js server)
RUN npm install -g serve

# Copy built site from builder
COPY --from=builder /app/apps/site/dist ./dist

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:3000/ || exit 1

# Expose port (Portainer will map this)
EXPOSE 3000

# Serve the dist folder
CMD ["serve", "dist", "-l", "3000"]
