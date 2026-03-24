# Use a lightweight Python image
FROM python:3.10-slim

# Install system-level dependencies + AWS CLI for S3 sync
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    awscli \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy and install dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# 1. Create the production asset directory
# 2. Make the entrypoint script executable
RUN mkdir -p /tmp/assets && chmod +x /app/entrypoint.sh

# Change ENTRYPOINT to use the shell script instead of calling python directly
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]