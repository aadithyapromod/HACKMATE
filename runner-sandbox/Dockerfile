# Hardened Node.js Sandbox for Compiling Generated React+Vite Projects
FROM node:20-alpine

# Install minimal build prerequisites
RUN apk add --no-cache dumb-init

# Create unprivileged non-root user
RUN addgroup -g 1001 sandboxgroup && \
    adduser -u 1001 -G sandboxgroup -s /bin/sh -D sandboxuser

# Create workspace directory with proper permissions
WORKDIR /workspace
RUN chown -R sandboxuser:sandboxgroup /workspace

# Switch permanently to unprivileged non-root user
USER sandboxuser

# Environment variables
ENV NODE_ENV=production \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    NPM_CONFIG_FUND=false \
    NPM_CONFIG_AUDIT=false

# Use dumb-init as PID 1 to handle signal forwarding and orphan process reaping
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["sh", "-c", "npm install && npm run build"]
