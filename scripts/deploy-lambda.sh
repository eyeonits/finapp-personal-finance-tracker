#!/bin/bash
# Deploy Lambda function to AWS
# Usage: ./scripts/deploy-lambda.sh [environment]

set -e

ENVIRONMENT=${1:-dev}
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "🚀 Deploying FinApp API to AWS Lambda..."
echo "   Environment: $ENVIRONMENT"
echo "   Region: $AWS_REGION"
echo "   Account: $AWS_ACCOUNT_ID"
echo ""

# Get ECR repository URL from Terraform
cd infrastructure
ECR_REPO=$(terraform output -raw ecr_repository_url 2>/dev/null || echo "")

if [ -z "$ECR_REPO" ]; then
    echo "❌ ECR repository not found. Run 'terraform apply' first."
    exit 1
fi

echo "📦 ECR Repository: $ECR_REPO"
cd ..

# Authenticate with ECR
echo "🔐 Authenticating with ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build Docker image
echo "🔨 Building Docker image..."
cd api
docker build -f Dockerfile.lambda -t finapp-api:latest .

# Tag and push to ECR
echo "📤 Pushing to ECR..."
docker tag finapp-api:latest $ECR_REPO:latest
docker push $ECR_REPO:latest

# Update Lambda function
echo "🔄 Updating Lambda function..."
LAMBDA_NAME="finapp-api-$ENVIRONMENT"
aws lambda update-function-code \
    --function-name $LAMBDA_NAME \
    --image-uri $ECR_REPO:latest \
    --region $AWS_REGION

# Wait for update to complete
echo "⏳ Waiting for Lambda update to complete..."
aws lambda wait function-updated \
    --function-name $LAMBDA_NAME \
    --region $AWS_REGION

# Get API Gateway URL
cd ../infrastructure
API_URL=$(terraform output -raw api_gateway_url 2>/dev/null || echo "")

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📡 API Gateway URL: $API_URL"
echo "🔍 Test endpoint:   ${API_URL}api/v1/health"
echo ""
echo "To view logs:"
echo "  aws logs tail /aws/lambda/$LAMBDA_NAME --follow"

