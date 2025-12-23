#!/bin/bash
# Deploy Frontend to S3 + CloudFront
# Usage: ./scripts/deploy-frontend.sh [environment]

set -e

ENVIRONMENT=${1:-dev}

echo "🚀 Deploying FinApp Frontend..."
echo "   Environment: $ENVIRONMENT"
echo ""

# Get bucket name and CloudFront ID from Terraform
cd infrastructure
BUCKET_NAME=$(terraform output -raw frontend_bucket_name 2>/dev/null || echo "")
CLOUDFRONT_ID=$(terraform output -raw cloudfront_distribution_id 2>/dev/null || echo "")
API_URL=$(terraform output -raw api_gateway_url 2>/dev/null || echo "")
FRONTEND_URL=$(terraform output -raw frontend_url 2>/dev/null || echo "")

if [ -z "$BUCKET_NAME" ]; then
    echo "❌ S3 bucket not found. Run 'terraform apply' first."
    exit 1
fi

echo "📦 S3 Bucket: $BUCKET_NAME"
echo "🌐 CloudFront ID: $CLOUDFRONT_ID"
echo "🔗 API URL: $API_URL"
cd ..

# Build frontend
echo ""
echo "🔨 Building frontend..."
cd frontend

# Create production environment file
cat > .env.production << EOF
VITE_API_URL=$API_URL
EOF

npm ci
npm run build

# Sync to S3
echo ""
echo "📤 Uploading to S3..."
aws s3 sync dist/ s3://$BUCKET_NAME/ \
    --delete \
    --cache-control "public, max-age=31536000, immutable" \
    --exclude "index.html" \
    --exclude "*.json"

# Upload index.html and JSON with shorter cache
aws s3 cp dist/index.html s3://$BUCKET_NAME/index.html \
    --cache-control "public, max-age=0, must-revalidate"

# Upload any JSON files (like manifest)
find dist -name "*.json" -exec aws s3 cp {} s3://$BUCKET_NAME/ \
    --cache-control "public, max-age=0, must-revalidate" \;

# Invalidate CloudFront cache
if [ -n "$CLOUDFRONT_ID" ]; then
    echo ""
    echo "🔄 Invalidating CloudFront cache..."
    aws cloudfront create-invalidation \
        --distribution-id $CLOUDFRONT_ID \
        --paths "/*" \
        --query 'Invalidation.Id' \
        --output text
fi

echo ""
echo "✅ Frontend deployment complete!"
echo ""
echo "🌐 Frontend URL: $FRONTEND_URL"
echo "📡 API URL: $API_URL"
echo ""
echo "Note: CloudFront propagation may take a few minutes."

