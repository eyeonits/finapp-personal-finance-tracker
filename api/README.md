# FinApp API

FastAPI-based REST API for the FinApp personal finance tracker with multi-user support and AWS Cognito authentication.

## Features

- RESTful API with automatic OpenAPI documentation
- AWS Cognito authentication with JWT tokens
- Multi-user support with data isolation
- PostgreSQL database with async SQLAlchemy
- CSV import for credit card and bank transactions
- Dashboard analytics and spending insights
- Comprehensive error handling and logging

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- AWS Account (for Cognito)
- Docker and Docker Compose (optional)

## Quick Start

### 1. Set up environment

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` and add your AWS Cognito credentials.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start PostgreSQL (using Docker)

```bash
docker-compose up -d postgres
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Start the API server

**Important:** Run this command from the **project root** directory (where `api/` is a subdirectory), not from inside the `api/` directory.

```bash
# From the project root (finapp/)
uvicorn api.main:app --reload --port 8000
```

**Alternative:** If you prefer to run from the `api/` directory, you can use:
```bash
# From the api/ directory
python -m uvicorn main:app --reload --port 8000
```

The API will be available at http://localhost:8000

## API Documentation

Once the server is running, visit:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

### Using Docker Compose

Start all services (PostgreSQL + API):

```bash
docker-compose up
```

### Running tests

```bash
pytest
```

### Creating database migrations

```bash
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

### Environment-specific configurations

Use different environment files:

```bash
# Development
cp .env.development .env

# Staging
cp .env.staging .env

# Production
cp .env.production .env
```

## Project Structure

```
api/
├── main.py                 # Application entry point
├── config.py              # Configuration management
├── dependencies.py        # Dependency injection
├── routers/               # API endpoints
├── services/              # Business logic
├── repositories/          # Data access layer
├── models/                # Pydantic and SQLAlchemy models
├── middleware/            # Custom middleware
├── utils/                 # Utilities
└── alembic/              # Database migrations
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get tokens
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout
- `POST /api/v1/auth/forgot-password` - Request password reset
- `POST /api/v1/auth/reset-password` - Reset password
- `GET /api/v1/auth/me` - Get current user

### Transactions
- `GET /api/v1/transactions` - List transactions
- `GET /api/v1/transactions/{id}` - Get transaction
- `POST /api/v1/transactions` - Create transaction
- `PUT /api/v1/transactions/{id}` - Update transaction
- `DELETE /api/v1/transactions/{id}` - Delete transaction

### Imports
- `POST /api/v1/imports/credit-card` - Import credit card CSV
- `POST /api/v1/imports/bank` - Import bank CSV
- `GET /api/v1/imports/history` - Get import history
- `GET /api/v1/imports/{id}` - Get import details

### Analytics
- `GET /api/v1/analytics/dashboard` - Dashboard metrics
- `GET /api/v1/analytics/spending` - Spending by category
- `GET /api/v1/analytics/trends` - Spending trends
- `GET /api/v1/analytics/correlations` - Correlated payments

### Health
- `GET /api/v1/health` - Health check
- `GET /api/v1/health/ready` - Readiness check

## Configuration

All configuration is managed through environment variables. See `.env.example` for available options.

### Required Configuration

- `DATABASE_URL` - PostgreSQL connection string
- `COGNITO_REGION` - AWS region for Cognito
- `COGNITO_USER_POOL_ID` - Cognito User Pool ID
- `COGNITO_APP_CLIENT_ID` - Cognito App Client ID
- `COGNITO_APP_CLIENT_SECRET` - Cognito App Client Secret

### Optional Configuration

- `DEBUG` - Enable debug mode (default: false)
- `LOG_LEVEL` - Logging level (default: INFO)
- `CORS_ORIGINS` - Allowed CORS origins
- `RATE_LIMIT_PER_MINUTE` - Rate limit per user (default: 100)

## Security

- All endpoints except health checks require JWT authentication
- Passwords are managed by AWS Cognito (bcrypt with salt)
- JWT tokens use RS256 algorithm
- HTTPS enforced in production
- Rate limiting enabled
- Input validation with Pydantic
- SQL injection prevention with parameterized queries

## Deployment

See `infrastructure/README.md` for AWS infrastructure setup with Terraform.

## License

See LICENSE file in the root directory.
