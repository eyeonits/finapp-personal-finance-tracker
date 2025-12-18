# FinApp API Setup Guide

This guide walks you through setting up the FinApp API from scratch.

## Task 1: Set up project infrastructure and AWS Cognito ✓

All subtasks completed:
- ✓ 1.1 Create FastAPI project structure
- ✓ 1.2 Set up AWS Cognito User Pool
- ✓ 1.3 Set up local development database
- ✓ 1.4 Create configuration management

## What Was Created

### Project Structure
```
api/
├── main.py                      # FastAPI application entry point
├── config.py                    # Configuration management with Pydantic
├── dependencies.py              # Dependency injection
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker image for API
├── docker-compose.yml           # Local development with PostgreSQL
├── alembic.ini                  # Alembic configuration
├── init.sql                     # Initial database schema
├── .env.example                 # Example environment variables
├── .env.development             # Development configuration
├── .env.staging                 # Staging configuration
├── .env.production              # Production configuration
├── routers/                     # API endpoints (stubs)
│   ├── auth.py
│   ├── transactions.py
│   ├── imports.py
│   ├── analytics.py
│   └── health.py
├── services/                    # Business logic (stubs)
│   ├── auth_service.py
│   ├── transaction_service.py
│   ├── import_service.py
│   └── analytics_service.py
├── repositories/                # Data access layer (stubs)
│   ├── base_repository.py
│   ├── user_repository.py
│   └── transaction_repository.py
├── models/                      # Pydantic and SQLAlchemy models
│   ├── requests.py
│   ├── responses.py
│   └── domain.py
├── middleware/                  # Custom middleware (stubs)
│   ├── auth.py
│   ├── logging.py
│   └── error_handler.py
├── utils/                       # Utilities
│   ├── db.py
│   ├── jwt_utils.py
│   └── exceptions.py
└── alembic/                     # Database migrations
    ├── env.py
    ├── script.py.mako
    └── versions/

infrastructure/
├── cognito.tf                   # Terraform configuration for Cognito
└── README.md                    # Infrastructure setup guide
```

### Key Features Implemented

1. **FastAPI Application Structure**
   - Modular architecture with routers, services, and repositories
   - Dependency injection setup
   - Automatic OpenAPI documentation
   - CORS middleware configuration

2. **Configuration Management**
   - Pydantic settings with validation
   - Environment-specific configurations (dev/staging/production)
   - Secure credential management
   - Validation for required settings

3. **Database Setup**
   - PostgreSQL with async SQLAlchemy
   - Docker Compose for local development
   - Initial schema with users, transactions, and import_history tables
   - Alembic for database migrations

4. **AWS Cognito Infrastructure**
   - Terraform configuration for User Pool
   - Password policy enforcement (8 chars, uppercase, lowercase, numbers)
   - Email verification enabled
   - App client with proper auth flows

5. **Models**
   - Pydantic request/response models for validation
   - SQLAlchemy domain models for database entities
   - Type-safe data handling

## Next Steps

### 1. Install Dependencies

```bash
cd api
pip install -r requirements.txt
```

### 2. Set Up AWS Cognito

Choose one of these options:

**Option A: Using Terraform (Recommended)**
```bash
cd infrastructure
terraform init
terraform apply
```

**Option B: Using AWS Console**
Follow the instructions in `infrastructure/README.md`

### 3. Configure Environment

```bash
cd api
cp .env.example .env
# Edit .env and add your Cognito credentials
```

Required environment variables:
- `DATABASE_URL` - PostgreSQL connection string
- `COGNITO_REGION` - AWS region (e.g., us-east-1)
- `COGNITO_USER_POOL_ID` - From Cognito setup
- `COGNITO_APP_CLIENT_ID` - From Cognito setup
- `COGNITO_APP_CLIENT_SECRET` - From Cognito setup

### 4. Start PostgreSQL

```bash
docker-compose up -d postgres
```

Wait for PostgreSQL to be ready:
```bash
docker-compose logs -f postgres
```

### 5. Run Database Migrations

```bash
alembic upgrade head
```

### 6. Start the API

```bash
uvicorn api.main:app --reload
```

The API will be available at:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 7. Verify Setup

```bash
# Check health endpoint
curl http://localhost:8000/api/v1/health

# Expected response:
# {"status":"healthy"}
```

## What's Next?

The following tasks are ready to be implemented:

- **Task 2**: Implement authentication service and JWT middleware
- **Task 3**: Implement authentication API endpoints
- **Task 4**: Implement database schema changes for multi-user support
- **Task 5**: Implement transaction API endpoints
- **Task 6**: Implement CSV import API endpoints
- **Task 7**: Implement analytics API endpoints
- **Task 8**: Implement error handling and logging
- **Task 9**: Implement security features
- **Task 10**: Create API documentation
- **Task 11**: Set up deployment infrastructure

## Troubleshooting

### PostgreSQL Connection Issues

If you can't connect to PostgreSQL:
```bash
# Check if PostgreSQL is running
docker-compose ps

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Configuration Errors

If you get configuration validation errors:
```bash
# Verify your .env file has all required variables
cat .env

# Check against the example
diff .env .env.example
```

### Import Errors

If you get Python import errors:
```bash
# Ensure you're in the right directory
pwd  # Should show .../api

# Reinstall dependencies
pip install -r requirements.txt
```

## Architecture Notes

### Strangler Fig Pattern

The API is designed to run alongside the existing Flask application:
- Flask app continues to serve the web UI
- New API provides REST endpoints for future clients
- Gradual migration of functionality from Flask to FastAPI
- Both applications can share the same database

### Data Isolation

All user data is isolated by `user_id`:
- Every transaction is associated with a user
- Repository layer enforces user_id filtering
- Authorization checks prevent cross-user access

### Security

- JWT tokens from AWS Cognito
- All endpoints (except health) require authentication
- HTTPS enforced in production
- Rate limiting enabled
- Input validation with Pydantic

## Support

For issues or questions:
1. Check the README.md files in each directory
2. Review the design document: `.kiro/specs/api-authentication/design.md`
3. Review the requirements: `.kiro/specs/api-authentication/requirements.md`
