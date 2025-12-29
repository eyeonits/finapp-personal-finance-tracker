# FinApp Infrastructure

Terraform configuration for deploying FinApp to AWS. This sets up a fully serverless architecture with PostgreSQL for data persistence.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                 Internet                                     │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │          API Gateway              │
                    │          (HTTP API)               │
                    └─────────────────┬─────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │            Lambda                 │
                    │      (FastAPI + Mangum)           │
                    │         Container                 │
                    └─────────────────┬─────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ▼                       ▼                       ▼
    ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
    │     Cognito      │   │       RDS        │   │    CloudWatch    │
    │   (User Auth)    │   │   PostgreSQL     │   │     (Logs)       │
    └──────────────────┘   └──────────────────┘   └──────────────────┘
```

## Terraform Files

| File | Description |
|------|-------------|
| `cognito.tf` | AWS Cognito User Pool for authentication |
| `rds.tf` | PostgreSQL database (RDS db.t4g.micro) |
| `ecr.tf` | Container registry for Lambda images |
| `lambda.tf` | Lambda function running FastAPI |
| `api_gateway.tf` | HTTP API Gateway routing to Lambda |
| `variables.tf` | Input variables with defaults |
| `outputs.tf` | Output values (endpoints, IDs, etc.) |

---

## File Details

### `cognito.tf` — Authentication

Creates an AWS Cognito User Pool for user authentication:

- **User Pool**: Email-based authentication
- **Password Policy**: 8+ chars, uppercase, lowercase, numbers
- **App Client**: OAuth flows for the frontend
- **Email Verification**: Required for new signups

**Key Outputs:**
- `user_pool_id` — Cognito User Pool ID
- `app_client_id` — App client ID for frontend
- `app_client_secret` — App client secret (sensitive)

---

### `rds.tf` — Database

Creates a PostgreSQL RDS instance:

- **Engine**: PostgreSQL 15
- **Instance**: `db.t4g.micro` (Free tier eligible)
- **Storage**: 20GB gp2 (Free tier eligible)
- **Encryption**: Enabled at rest
- **Backups**: 7-day retention

**Security:**
- Private by default (VPC only)
- Security group restricts access to Lambda and optional IP

**Key Outputs:**
- `db_endpoint` — RDS connection endpoint
- `db_connection_string` — Full connection string (password redacted)

---

### `ecr.tf` — Container Registry

Creates an ECR repository for Lambda container images:

- **Lifecycle Policy**: Keeps only last 5 images
- **Scanning**: Enabled on push

**Key Outputs:**
- `ecr_repository_url` — URL for docker push

---

### `lambda.tf` — Backend API

Creates the Lambda function running FastAPI:

- **Runtime**: Container image (Python 3.11)
- **Memory**: 512MB (configurable)
- **Timeout**: 30 seconds
- **VPC**: Connected to reach RDS

**IAM Permissions:**
- CloudWatch Logs (basic execution)
- VPC access (ENI management)
- Cognito (token validation)

**Environment Variables** (auto-configured):
- `DATABASE_URL` — RDS connection string
- `COGNITO_*` — Cognito configuration
- `CORS_ORIGINS` — Allowed origins

**Key Outputs:**
- `lambda_function_name` — Function name for updates
- `lambda_function_arn` — Function ARN

---

### `api_gateway.tf` — HTTP API

Creates an API Gateway HTTP API:

- **Protocol**: HTTP (not REST — simpler & cheaper)
- **CORS**: Configured from `cors_origins` variable
- **Throttling**: 50 req/s, 100 burst
- **Logging**: CloudWatch access logs

**Key Outputs:**
- `api_gateway_url` — Public API endpoint

---

## Prerequisites

1. **Install Terraform**
   ```bash
   brew install terraform
   # or download from https://terraform.io/downloads
   ```

2. **Configure AWS CLI**
   ```bash
   aws configure
   # Enter your Access Key, Secret Key, and Region
   ```

3. **Docker** (for building Lambda images)
   ```bash
   brew install --cask docker
   ```

---

## Quick Start

### 1. Configure Variables

```bash
cd infrastructure
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
environment = "dev"
aws_region  = "us-east-1"

# REQUIRED: Set a strong password
db_password = "YourSecurePassword123!"

# Optional: Your IP for direct DB access
allowed_ip = ""  # e.g., "203.0.113.50"
```

### 2. Initialize Terraform

```bash
terraform init
```

### 3. Review the Plan

```bash
terraform plan
```

### 4. Deploy

```bash
terraform apply
```

### 5. Push Lambda Image

```bash
# Use the deploy script
../scripts/deploy-lambda.sh dev

# Or manually:
ECR_URL=$(terraform output -raw ecr_repository_url)
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URL

cd ../api
docker build -f Dockerfile.lambda -t finapp-api .
docker tag finapp-api:latest $ECR_URL:latest
docker push $ECR_URL:latest
```

### 6. Run Migrations

```bash
cd ../api
export DATABASE_URL=$(cd ../infrastructure && terraform output -raw db_connection_string | sed 's/<password>/YOUR_PASSWORD/')
alembic upgrade head
```

---

## Viewing Outputs

After deployment, view all outputs:

```bash
terraform output
```

Or specific values:

```bash
# API endpoint
terraform output api_gateway_url

# Database endpoint
terraform output db_endpoint

# ECR repository
terraform output ecr_repository_url
```

---

## Updating the Lambda

After code changes:

```bash
../scripts/deploy-lambda.sh dev
```

Or manually:

```bash
aws lambda update-function-code \
  --function-name finapp-api-dev \
  --image-uri $(terraform output -raw ecr_repository_url):latest
```

---

## Cost Estimate

| Resource | Monthly Cost |
|----------|-------------|
| RDS (db.t4g.micro) | $12 (or $0 free tier) |
| Lambda | ~$0 (free tier: 1M requests) |
| API Gateway | ~$1-3 |
| ECR | ~$0.10 |
| CloudWatch | ~$0.50 |
| Cognito | $0 (free tier: 50K MAU) |
| **Total** | **~$14-16/month** |

*Free tier eligible for first 12 months*

---

## Environment Variables for API

After deployment, configure your API `.env`:

```bash
# Get values from Terraform
cd infrastructure

echo "DATABASE_URL=postgresql+asyncpg://$(terraform output -raw db_connection_string | sed 's/<password>/YOUR_PASSWORD/')"
echo "COGNITO_REGION=$(terraform output -raw aws_region 2>/dev/null || echo 'us-east-1')"
echo "COGNITO_USER_POOL_ID=$(terraform output -raw user_pool_id)"
echo "COGNITO_APP_CLIENT_ID=$(terraform output -raw app_client_id)"
echo "COGNITO_APP_CLIENT_SECRET=$(terraform output -raw app_client_secret)"
```

---

## Connecting to RDS Directly

For local development or running migrations:

### Option A: Enable Public Access (Development Only)

1. Set in `terraform.tfvars`:
   ```hcl
   db_publicly_accessible = true
   allowed_ip = "YOUR.IP.ADDRESS"  # Find at https://whatismyip.com
   ```

2. Apply:
   ```bash
   terraform apply
   ```

3. Connect:
   ```bash
   psql "postgresql://finapp_admin:PASSWORD@$(terraform output -raw db_address):5432/finapp"
   ```

### Option B: Use SSM Session Manager (Recommended for Prod)

Connect through a bastion or use AWS Session Manager port forwarding.

---

## Testing the Deployment

```bash
# Get API URL
API_URL=$(terraform output -raw api_gateway_url)

# Health check
curl ${API_URL}api/v1/health

# Should return:
# {"status": "healthy", ...}
```

---

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

⚠️ **Warning**: This deletes:
- All Cognito users
- Database and all data
- Lambda function
- API Gateway

---

## Troubleshooting

### Lambda not connecting to RDS

1. Check security group allows Lambda → RDS on port 5432
2. Verify Lambda is in the same VPC as RDS
3. Check CloudWatch logs: `/aws/lambda/finapp-api-dev`

### Cold start too slow

Increase Lambda memory (also increases CPU):
```hcl
lambda_memory_size = 1024  # or higher
```

### ECR push fails

Re-authenticate:
```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com
```

### Database connection errors

Verify the `DATABASE_URL` format:
```
postgresql+asyncpg://username:password@hostname:5432/database
```

---

## Security Considerations

- ✅ Database credentials in `terraform.tfvars` (gitignored)
- ✅ RDS encrypted at rest
- ✅ RDS not publicly accessible by default
- ✅ Lambda in VPC with security groups
- ✅ Cognito handles password policies
- ✅ API Gateway throttling prevents abuse

### Recommendations for Production

1. Enable `deletion_protection` on RDS
2. Use AWS Secrets Manager for credentials
3. Enable Multi-AZ for RDS
4. Add WAF to API Gateway
5. Enable Cognito MFA
