FROM node:20-slim

# Install Python 3 for the runner worker orchestration scripts
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a non-root sandbox runner user
RUN useradd -m -u 1001 runneruser

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .

# Set permissions for non-root execution
RUN chown -R runneruser:runneruser /app
USER runneruser

ENV NODE_ENV=development
EXPOSE 4173 5173

CMD ["python3", "-m", "runner.runner"]
