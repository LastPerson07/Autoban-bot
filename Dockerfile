# Dockerfile
FROM python:3.11-slim-bookworm

# Set working directory
WORKDIR /app

# Install system dependencies (optional but recommended for better performance/stability)
# - ca-certificates: for MongoDB Atlas TLS
# - gcc & python-dev: needed only if installing TgCrypto from source (we'll use prebuilt)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
# TgCrypto is optional but highly recommended for faster encryption/decryption
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Run the bot as non-root user for security (optional but best practice)
RUN useradd -m appuser
USER appuser

# Command to run the bot
CMD ["python", "bot.py"]