#!/bin/bash
set -e

echo "Deploying Backend API to Google Cloud Run (Free Tier)..."

# Deploy from source using the backend/ directory context
gcloud run deploy extraction-api \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2 

echo "Deployment successful."
echo "Updating Environment Variables..."

gcloud run services update extraction-api \
  --region asia-south1 \
  --set-env-vars="GEMINI_API_KEY=${GEMINI_API_KEY:-your_key_here},\
DATABASE_URL=${DATABASE_URL:-postgresql+asyncpg://...},\
REDIS_URL=${REDIS_URL:-redis://...}"

echo "Cloud Run Service extraction-api is live!"
