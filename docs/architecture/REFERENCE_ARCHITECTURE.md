# FinApp Reference Architecture

> Personal Finance Tracker — Full-Stack Serverless Application

## Table of Contents

- [Overview](#overview)
- [Architecture Diagrams](#architecture-diagrams)
- [Component Details](#component-details)
- [Local Development](#local-development)
- [AWS Production](#aws-production)
- [Data Flow](#data-flow)
- [Security Architecture](#security-architecture)
- [Infrastructure as Code](#infrastructure-as-code)
- [Cost Estimates](#cost-estimates)
- [Deployment Pipeline](#deployment-pipeline)

---

## Overview

FinApp is a personal finance tracking application built with a modern serverless architecture. It supports both local development (with local authentication) and AWS production deployment (with Cognito authentication).

### Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, TypeScript, Vite, TailwindCSS, Chart.js |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy, Pydantic |
| **Database** | PostgreSQL 15 (RDS in production) |
| **Authentication** | Local JWT (dev) / AWS Cognito (prod) |
| **Infrastructure** | Terraform, Docker, AWS Lambda |

---

## Architecture Diagrams

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                  USERS                                       │
│                            (Web Browser)                                     │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ HTTPS
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         CloudFront CDN                               │    │
│  │                    (HTTPS, Edge Caching, WAF)                        │    │
│  └───────────────────────────────┬─────────────────────────────────────┘    │
│                                  │                                           │
│  ┌───────────────────────────────┴─────────────────────────────────────┐    │
│  │                           S3 Bucket                                  │    │
│  │                    (React Static Assets)                             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ API Calls (HTTPS)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                API LAYER                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      API Gateway (HTTP API)                          │    │
│  │                  (CORS, Throttling, Logging)                         │    │
│  └───────────────────────────────┬─────────────────────────────────────┘    │
│                                  │                                           │
│  ┌───────────────────────────────┴─────────────────────────────────────┐    │
│  │                         Lambda Function                              │    │
│  │                    (FastAPI + Mangum Adapter)                        │    │
│  │                      Python 3.11 Container                           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
┌──────────────────────┐ ┌──────────────────┐ ┌──────────────────────┐
│       COGNITO        │ │       RDS        │ │     CLOUDWATCH       │
│                      │ │                  │ │                      │
│  ┌────────────────┐  │ │  ┌────────────┐  │ │  ┌────────────────┐  │
│  │   User Pool    │  │ │  │ PostgreSQL │  │ │  │     Logs       │  │
│  │                │  │ │  │    15      │  │ │  │    Metrics     │  │
│  │  - Auth Flows  │  │ │  │            │  │ │  │    Alarms      │  │
│  │  - JWT Tokens  │  │ │  │ db.t4g.    │  │ │  │                │  │
│  │  - MFA (opt)   │  │ │  │   micro    │  │ │  └────────────────┘  │
│  └────────────────┘  │ │  └────────────┘  │ │                      │
└──────────────────────┘ └──────────────────┘ └──────────────────────┘
```

### Request Flow

```
┌──────────┐     ┌────────────┐     ┌─────────────┐     ┌────────┐     ┌─────┐
│  Browser │────▶│ CloudFront │────▶│ API Gateway │────▶│ Lambda │────▶│ RDS │
└──────────┘     └────────────┘     └─────────────┘     └────────┘     └─────┘
     │                                     │                 │
     │                                     │                 │
     │                              ┌──────┴──────┐          │
     │                              │   Cognito   │◀─────────┘
     │                              │ (validate   │  (get user info)
     │                              │   JWT)      │
     │                              └─────────────┘
     │
     └──────────────▶ S3 (static assets: JS, CSS, images)
```

---

## Component Details

### Frontend (React SPA)

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   └── ProtectedRoute.tsx
│   ├── contexts/            # React Context providers
│   │   ├── AuthContext.tsx  # Authentication state
│   │   └── ThemeContext.tsx # Dark/light mode
│   ├── lib/
│   │   └── api.ts           # API client (axios)
│   ├── pages/               # Route components
│   │   ├── Dashboard.tsx    # Main dashboard with charts
│   │   ├── Import.tsx       # Transaction import
│   │   ├── Login.tsx        # Authentication
│   │   ├── Register.tsx     # User registration
│   │   ├── ChangePassword.tsx
│   │   └── ForgotPassword.tsx
│   ├── App.tsx              # Router setup
│   └── main.tsx             # Entry point
├── package.json
├── vite.config.ts
└── tailwind.config.js
```

**Key Features:**
- Single Page Application (SPA)
- JWT token management with auto-refresh
- Dark/light mode support
- Responsive design
- Chart.js for data visualization

---

### Backend (FastAPI)

```
api/
├── main.py                  # FastAPI app factory
├── config.py                # Pydantic settings
├── dependencies.py          # Dependency injection
├── lambda_handler.py        # AWS Lambda entry point
│
├── routers/                 # API endpoints
│   ├── auth.py              # /api/v1/auth/*
│   ├── transactions.py      # /api/v1/transactions/*
│   ├── imports.py           # /api/v1/imports/*
│   ├── analytics.py         # /api/v1/analytics/*
│   └── health.py            # /api/v1/health/*
│
├── services/                # Business logic
│   ├── auth_service.py      # Cognito integration
│   ├── local_auth_service.py # Local JWT auth
│   ├── user_service.py
│   ├── transaction_service.py
│   ├── import_service.py
│   └── analytics_service.py
│
├── repositories/            # Data access layer
│   ├── base_repository.py
│   ├── user_repository.py
│   ├── transaction_repository.py
│   └── import_repository.py
│
├── models/
│   ├── domain.py            # SQLAlchemy models
│   ├── requests.py          # Pydantic request models
│   └── responses.py         # Pydantic response models
│
├── middleware/
│   ├── auth.py              # JWT validation
│   ├── error_handler.py
│   └── logging.py
│
├── utils/
│   ├── db.py                # Database connection
│   ├── jwt_utils.py         # Token handling
│   └── exceptions.py        # Custom exceptions
│
├── alembic/                 # Database migrations
│   └── versions/
│
├── Dockerfile               # Local development
└── Dockerfile.lambda        # AWS Lambda container
```

**API Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | User registration |
| `/api/v1/auth/login` | POST | Authentication |
| `/api/v1/auth/refresh` | POST | Token refresh |
| `/api/v1/auth/change-password` | POST | Change password |
| `/api/v1/auth/me` | GET | Current user info |
| `/api/v1/transactions` | GET | List transactions |
| `/api/v1/transactions/{id}` | GET | Get transaction |
| `/api/v1/imports/credit-card` | POST | Import CC transactions |
| `/api/v1/imports/bank` | POST | Import bank transactions |
| `/api/v1/health` | GET | Health check |

---

### Database Schema

```sql
┌─────────────────────────────────────────────────────────────────┐
│                            users                                 │
├─────────────────────────────────────────────────────────────────┤
│ user_id          VARCHAR(36)   PK                               │
│ cognito_sub      VARCHAR(255)  UNIQUE, NULLABLE                 │
│ email            VARCHAR(255)  UNIQUE, NOT NULL                 │
│ password_hash    VARCHAR(255)  NULLABLE (local auth only)       │
│ email_verified   BOOLEAN       DEFAULT false                    │
│ is_active        BOOLEAN       DEFAULT true                     │
│ created_at       TIMESTAMP     DEFAULT now()                    │
│ updated_at       TIMESTAMP     DEFAULT now()                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 1:N
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         transactions                             │
├─────────────────────────────────────────────────────────────────┤
│ transaction_id   VARCHAR(36)   PK                               │
│ user_id          VARCHAR(36)   FK → users.user_id               │
│ transaction_date DATE          NOT NULL                         │
│ post_date        DATE          NOT NULL                         │
│ description      VARCHAR       NOT NULL                         │
│ category         VARCHAR       NULLABLE                         │
│ type             VARCHAR       NULLABLE                         │
│ amount           DECIMAL(10,2) NOT NULL                         │
│ memo             VARCHAR       NULLABLE                         │
│ account_id       VARCHAR       NOT NULL                         │
│ source           VARCHAR       NOT NULL                         │
│ created_at       TIMESTAMP     DEFAULT now()                    │
│ updated_at       TIMESTAMP     DEFAULT now()                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 1:N
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        import_history                            │
├─────────────────────────────────────────────────────────────────┤
│ import_id        VARCHAR(36)   PK                               │
│ user_id          VARCHAR(36)   FK → users.user_id               │
│ import_type      VARCHAR(50)   NOT NULL                         │
│ account_id       VARCHAR(100)  NOT NULL                         │
│ filename         VARCHAR(255)  NULLABLE                         │
│ rows_total       INTEGER       NOT NULL                         │
│ rows_inserted    INTEGER       NOT NULL                         │
│ rows_skipped     INTEGER       NOT NULL                         │
│ status           VARCHAR(50)   NOT NULL                         │
│ error_message    TEXT          NULLABLE                         │
│ created_at       TIMESTAMP     DEFAULT now()                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Local Development

### Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│    Browser       │────▶│   Vite Dev       │     │   PostgreSQL     │
│                  │     │   Server         │     │   (Docker)       │
│  localhost:5173  │     │   :5173          │     │   :5432          │
└──────────────────┘     └────────┬─────────┘     └────────▲─────────┘
                                  │                        │
                                  │ Proxy                  │
                                  ▼                        │
                         ┌──────────────────┐              │
                         │   FastAPI        │──────────────┘
                         │   (Uvicorn)      │
                         │   :8000          │
                         │                  │
                         │ USE_COGNITO=false│
                         │ (Local JWT Auth) │
                         └──────────────────┘
```

### Quick Start

```bash
# 1. Start PostgreSQL
cd api
docker-compose up -d

# 2. Configure environment
cp env.example .env
# Edit .env (USE_COGNITO=false is default)

# 3. Run migrations
alembic upgrade head

# 4. Start API
uvicorn api.main:app --reload

# 5. Start frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Environment Variables (Local)

```env
# api/.env
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://finapp:password@localhost:5432/finapp_dev
USE_COGNITO=false
JWT_SECRET_KEY=dev-secret-key
CORS_ORIGINS=http://localhost:5173
```

---

## AWS Production

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                    VPC                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         Public Subnets                               │    │
│  │   ┌─────────────┐                                                    │    │
│  │   │ NAT Gateway │ (for Lambda outbound to Cognito)                   │    │
│  │   └─────────────┘                                                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Private Subnets                               │    │
│  │                                                                      │    │
│  │   ┌─────────────────┐              ┌─────────────────────────────┐  │    │
│  │   │     Lambda      │◀────────────▶│          RDS                │  │    │
│  │   │  (FastAPI)      │              │    PostgreSQL 15            │  │    │
│  │   │                 │              │    db.t4g.micro             │  │    │
│  │   │  Security Group │              │    Security Group           │  │    │
│  │   │  (sg-lambda)    │              │    (sg-rds)                 │  │    │
│  │   └─────────────────┘              └─────────────────────────────┘  │    │
│  │           │                                                          │    │
│  └───────────┼──────────────────────────────────────────────────────────┘    │
│              │                                                               │
└──────────────┼───────────────────────────────────────────────────────────────┘
               │
               │ VPC Endpoint / NAT
               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              AWS Services                                     │
│                                                                               │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐      │
│   │  Cognito    │   │    ECR      │   │ CloudWatch  │   │   Secrets   │      │
│   │  User Pool  │   │ Repository  │   │    Logs     │   │   Manager   │      │
│   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘      │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Terraform Resources

| File | Resources |
|------|-----------|
| `providers.tf` | AWS provider configuration |
| `cognito.tf` | User Pool, App Client |
| `rds.tf` | PostgreSQL instance, Security Group, Subnet Group |
| `ecr.tf` | Container registry |
| `lambda.tf` | Function, IAM roles, Security Group |
| `api_gateway.tf` | HTTP API, Routes, Stage |
| `frontend.tf` | S3 bucket, CloudFront distribution |
| `variables.tf` | Input variables |
| `outputs.tf` | Output values |

---

## Data Flow

### Authentication Flow (Local)

```
┌────────┐     ┌─────────┐     ┌─────────┐     ┌──────┐
│ Client │────▶│ FastAPI │────▶│ Local   │────▶│  DB  │
│        │     │         │     │ Auth    │     │      │
│        │◀────│         │◀────│ Service │◀────│      │
└────────┘     └─────────┘     └─────────┘     └──────┘
    │               │
    │  JWT Token    │
    │◀──────────────┘
    │
    │  Subsequent requests with Bearer token
    │──────────────────────────────────────▶
```

### Authentication Flow (Cognito)

```
┌────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Client │────▶│ FastAPI │────▶│ Cognito │     │ Cognito │
│        │     │         │     │ Auth    │────▶│ User    │
│        │◀────│         │◀────│ Service │◀────│ Pool    │
└────────┘     └─────────┘     └─────────┘     └─────────┘
    │               │
    │  JWT Token    │  (signed by Cognito)
    │◀──────────────┘
    │
    │  Validate token via JWKS
    │──────────────────────────────────────▶
```

### Transaction Import Flow

```
┌────────┐     ┌─────────┐     ┌─────────┐     ┌──────────┐     ┌──────┐
│ Client │────▶│ API     │────▶│ Import  │────▶│ Txn      │────▶│  DB  │
│        │     │ Gateway │     │ Service │     │ Repo     │     │      │
│        │     │         │     │         │     │          │     │      │
│  CSV   │     │         │     │ Parse   │     │ Bulk     │     │      │
│  File  │     │         │     │ & Map   │     │ Insert   │     │      │
└────────┘     └─────────┘     └─────────┘     └──────────┘     └──────┘
```

---

## Security Architecture

### Authentication Modes

| Mode | Setting | Algorithm | Token Issuer |
|------|---------|-----------|--------------|
| **Local** | `USE_COGNITO=false` | HS256 | FastAPI |
| **Cognito** | `USE_COGNITO=true` | RS256 | AWS Cognito |

### Password Security (Local Auth)

- **Algorithm:** PBKDF2-SHA256
- **Iterations:** 100,000
- **Salt:** 16 bytes random per password
- **Requirements:** 8+ chars, uppercase, lowercase, digit

### API Security

| Layer | Protection |
|-------|------------|
| **Transport** | HTTPS only (TLS 1.2+) |
| **Authentication** | JWT Bearer tokens |
| **Authorization** | User-scoped data access |
| **Input Validation** | Pydantic models |
| **Rate Limiting** | API Gateway throttling |
| **CORS** | Configured origins only |

### AWS Security

| Resource | Security Measure |
|----------|------------------|
| **RDS** | VPC-only access, encrypted at rest |
| **Lambda** | VPC, least-privilege IAM |
| **S3** | Private, CloudFront OAC |
| **Secrets** | terraform.tfvars (gitignored) |
| **API Gateway** | HTTPS, throttling |

---

## Infrastructure as Code

### Directory Structure

```
infrastructure/
├── providers.tf          # AWS provider config
├── cognito.tf            # User authentication
├── rds.tf                # PostgreSQL database
├── ecr.tf                # Container registry
├── lambda.tf             # API compute
├── api_gateway.tf        # API routing
├── frontend.tf           # S3 + CloudFront
├── variables.tf          # Input variables
├── outputs.tf            # Output values
├── terraform.tfvars.example
└── README.md
```

### Deployment Commands

```bash
cd infrastructure

# Initialize
terraform init

# Plan
terraform plan

# Apply
terraform apply

# Outputs
terraform output api_gateway_url
terraform output frontend_url
```

---

## Cost Estimates

### AWS Production (Single User)

| Service | Monthly Cost |
|---------|-------------|
| RDS db.t4g.micro | $12.00 |
| Lambda (100K requests) | $0.00 (free tier) |
| API Gateway | $1.00 |
| CloudFront | $1.00 |
| S3 | $0.10 |
| ECR | $0.10 |
| CloudWatch | $0.50 |
| Cognito | $0.00 (free tier) |
| **Total** | **~$15/month** |

### Free Tier (First 12 Months)

| Service | Free Tier |
|---------|-----------|
| RDS | 750 hours db.t3.micro |
| Lambda | 1M requests |
| API Gateway | 1M requests |
| S3 | 5GB storage |
| CloudFront | 1TB transfer |
| **Total** | **~$0/month** |

---

## Deployment Pipeline

### Manual Deployment

```bash
# 1. Deploy Infrastructure
cd infrastructure
terraform apply

# 2. Deploy Backend
./scripts/deploy-lambda.sh dev

# 3. Deploy Frontend
./scripts/deploy-frontend.sh dev

# 4. Run Migrations
cd api
alembic upgrade head
```

### CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
      - run: ./scripts/deploy-lambda.sh prod

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci && npm run build
      - run: ./scripts/deploy-frontend.sh prod
```

---

## Monitoring & Observability

### CloudWatch Dashboards

| Metric | Source |
|--------|--------|
| API Latency | API Gateway |
| Error Rate | Lambda |
| Database Connections | RDS |
| Cold Starts | Lambda |

### Log Groups

| Log Group | Content |
|-----------|---------|
| `/aws/lambda/finapp-api-*` | API logs |
| `/aws/apigateway/finapp-*` | Access logs |
| `/aws/rds/instance/finapp-*` | Database logs |

### Alarms

| Alarm | Threshold |
|-------|-----------|
| API 5xx Errors | > 5 per minute |
| Lambda Duration | > 10 seconds |
| RDS CPU | > 80% |
| RDS Storage | < 2GB free |

---

## Appendix

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `USE_COGNITO` | No | `false` | Enable Cognito auth |
| `JWT_SECRET_KEY` | Local only | Auto-gen | JWT signing key |
| `COGNITO_REGION` | Cognito only | - | AWS region |
| `COGNITO_USER_POOL_ID` | Cognito only | - | User pool ID |
| `COGNITO_APP_CLIENT_ID` | Cognito only | - | App client ID |
| `CORS_ORIGINS` | No | `localhost` | Allowed origins |

### Terraform Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `environment` | `dev` | Environment name |
| `aws_region` | `us-east-1` | AWS region |
| `db_instance_class` | `db.t4g.micro` | RDS instance type |
| `db_password` | - | Database password |
| `lambda_memory_size` | `512` | Lambda memory (MB) |
| `domain_name` | `""` | Custom domain |


