#!/bin/bash
set -e

# Define where assets will go (matches your production OUTPUT_DIR)
export ASSETS_DIR="/tmp/assets"
mkdir -p $ASSETS_DIR

if [ "$APP_ENV" = "production" ]; then
    echo "📥 AWS Production Mode: Downloading secrets..."
    
    # 1. Download the .env
    aws s3 cp s3://${AWS_S3_BUCKET}/secrets/prod.env $ASSETS_DIR/prod.env
    
    # 2. Sync Google files
    aws s3 cp s3://${AWS_S3_BUCKET}/secrets/credentials.json $ASSETS_DIR/credentials.json
    aws s3 cp s3://${AWS_S3_BUCKET}/secrets/token.pickle $ASSETS_DIR/token.pickle
    aws s3 cp s3://${AWS_S3_BUCKET}/secrets/client_secret.json $ASSETS_DIR/client_secret.json
    
    echo "✅ S3 Sync Complete."
fi

# Launch Python
exec python main.py