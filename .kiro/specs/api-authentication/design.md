# Design Document

## Overview

This design document outlines the architecture for modernizing FinApp from a monolithic Flask application into a scalable, multi-user system with a RESTful API backend and AWS Cognito authentication. The design follows the Strangler Fig pattern, allowing gradual migration while maintaining backward compatibility.

The system will consist of:
- FastAPI-based REST API with automatic OpenAPI documentation
- AWS Cognito User Pool for authentication and user management
- JWT-based authentication middleware
- PostgreSQL database for user and transaction data
- Data isolation layer ensuring users only access their own data
- Existing Flask application running in parallel during migration

## Architecture

### High-Level Architecture

```
┌─────────────┐
│   Client    │
│  (Browser)  │
└──────┬──────┘
       │
       ├─────────────────┐
       │                 │
       v                 v
┌──────────────┐  ┌──────────────┐
│    Flask     │  │   FastAPI    │
│  (Legacy)    │  │   (New API)  │
└──────┬───────┘  └──────┬───────┘
       │                 │
       │                 ├──────────────┐
       │                 │              │
       v                 v              v
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Snowflake   │  │ PostgreSQL   │  │AWS Cognito   │
│ (Existing)   │  │   (New)      │  │  User Pool   │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Component Architecture


**API Layer (FastAPI)**
- Handles HTTP requests and responses
- Validates input using Pydantic models
- Enforces authentication via middleware
- Generates OpenAPI documentation
- Routes requests to service layer

**Authentication Layer**
- JWT token validation middleware
- Cognito integration for user operations
- User identity extraction from tokens
- Token refresh handling

**Service Layer**
- Business logic for transactions, imports, analytics
- Data access abstraction
- User-specific data filtering
- Error handling and logging

**Data Access Layer**
- PostgreSQL for user data and transactions
- Snowflake for analytics (optional, can migrate)
- Repository pattern for database operations
- Query builders with user ID filtering

**AWS Cognito**
- User registration and verification
- Authentication and token issuance
- Password reset flows
- User profile management

## Components and Interfaces

### 1. FastAPI Application Structure

```
api/
├── main.py                 # Application entry point
├── config.py              # Configuration management
├── dependencies.py        # Dependency injection
├── middleware/
│   ├── auth.py           # JWT authentication middleware
│   ├── logging.py        # Request logging middleware
│   └── error_handler.py  # Global error handling
├── routers/
│   ├── auth.py           # Authentication endpoints
│   ├── transactions.py   # Transaction CRUD endpoints
│   ├── imports.py        # CSV import endpoints
│   ├── analytics.py      # Dashboard metrics endpoints
│   └── health.py         # Health check endpoints
├── models/
│   ├── requests.py       # Pydantic request models
│   ├── responses.py      # Pydantic response models
│   └── domain.py         # Domain models
├── services/
│   ├── auth_service.py   # Cognito integration
│   ├── transaction_service.py
│   ├── import_service.py
│   └── analytics_service.py
├── repositories/
│   ├── transaction_repository.py
│   ├── user_repository.py
│   └── base_repository.py
└── utils/
    ├── jwt_utils.py      # JWT validation utilities
    ├── db.py             # Database connection
    └── exceptions.py     # Custom exceptions
```


### 2. API Endpoints

**Authentication Endpoints**
```
POST   /api/v1/auth/register          # Register new user
POST   /api/v1/auth/login             # Login and get tokens
POST   /api/v1/auth/refresh           # Refresh access token
POST   /api/v1/auth/logout            # Logout (invalidate tokens)
POST   /api/v1/auth/forgot-password   # Request password reset
POST   /api/v1/auth/reset-password    # Complete password reset
GET    /api/v1/auth/me                # Get current user info
```

**Transaction Endpoints**
```
GET    /api/v1/transactions           # List transactions (with filters)
GET    /api/v1/transactions/{id}      # Get single transaction
POST   /api/v1/transactions           # Create transaction (manual entry)
PUT    /api/v1/transactions/{id}      # Update transaction
DELETE /api/v1/transactions/{id}      # Delete transaction
```

**Import Endpoints**
```
POST   /api/v1/imports/credit-card    # Import CC CSV
POST   /api/v1/imports/bank           # Import bank CSV
GET    /api/v1/imports/history        # Get import history
GET    /api/v1/imports/{id}           # Get import details
```

**Analytics Endpoints**
```
GET    /api/v1/analytics/dashboard    # Get dashboard metrics
GET    /api/v1/analytics/spending     # Get spending by category
GET    /api/v1/analytics/trends       # Get spending trends
GET    /api/v1/analytics/correlations # Get correlated payments
```

**Health Endpoints**
```
GET    /api/v1/health                 # Health check
GET    /api/v1/health/ready           # Readiness check
```

### 3. Authentication Flow

**Registration Flow:**
```
1. Client → POST /api/v1/auth/register {email, password}
2. API → Cognito: SignUp
3. Cognito → User: Verification email
4. User → Cognito: Confirm email
5. API → Client: {success: true}
```

**Login Flow:**
```
1. Client → POST /api/v1/auth/login {email, password}
2. API → Cognito: InitiateAuth
3. Cognito → API: {access_token, refresh_token, id_token}
4. API → Client: {access_token, refresh_token, expires_in}
```

**Authenticated Request Flow:**
```
1. Client → GET /api/v1/transactions
   Headers: Authorization: Bearer <access_token>
2. API Middleware → Validate JWT signature
3. API Middleware → Extract user_id from token
4. API Service → Query transactions WHERE user_id = <user_id>
5. API → Client: {transactions: [...]}
```


## Data Models

### User Model (PostgreSQL)
```python
class User:
    user_id: str          # UUID, primary key
    cognito_sub: str      # Cognito user identifier (unique)
    email: str            # User email (unique)
    created_at: datetime
    updated_at: datetime
    is_active: bool
```

### Transaction Model (PostgreSQL)
```python
class Transaction:
    transaction_id: str   # UUID, primary key
    user_id: str          # Foreign key to User
    transaction_date: date
    post_date: date
    description: str
    category: str
    type: str
    amount: Decimal
    memo: str
    account_id: str       # User's account identifier
    source: str           # 'credit_card' or 'bank'
    created_at: datetime
    updated_at: datetime
```

### Import History Model (PostgreSQL)
```python
class ImportHistory:
    import_id: str        # UUID, primary key
    user_id: str          # Foreign key to User
    import_type: str      # 'credit_card' or 'bank'
    account_id: str
    filename: str
    rows_total: int
    rows_inserted: int
    rows_skipped: int
    status: str           # 'success', 'failed', 'partial'
    error_message: str
    created_at: datetime
```

### Request/Response Models (Pydantic)

**RegisterRequest:**
```python
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
```

**LoginRequest:**
```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
```

**TokenResponse:**
```python
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
```

**TransactionResponse:**
```python
class TransactionResponse(BaseModel):
    transaction_id: str
    transaction_date: date
    post_date: date
    description: str
    category: Optional[str]
    type: Optional[str]
    amount: Decimal
    memo: Optional[str]
    account_id: str
```

**DashboardMetricsResponse:**
```python
class DashboardMetricsResponse(BaseModel):
    num_transactions: int
    total_spent: Decimal
    total_received: Decimal
    net_flow: Decimal
    avg_daily_spend: Decimal
    daily_spending: List[DailySpending]
    category_breakdown: List[CategorySpending]
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: User data isolation
*For any* authenticated user and any transaction query, the returned transactions should only include transactions where the user_id matches the authenticated user's ID.
**Validates: Requirements 9.2**

### Property 2: JWT token validation
*For any* API request to a protected endpoint, if the JWT token is invalid or expired, the system should return a 401 Unauthorized error.
**Validates: Requirements 7.2, 7.3, 7.5**

### Property 3: Authentication token generation
*For any* valid login request with correct credentials, the system should return an access token, refresh token, and expiration time.
**Validates: Requirements 2.1, 2.3**

### Property 4: Password requirement enforcement
*For any* registration request, if the password does not meet minimum requirements (8 characters, uppercase, lowercase, numbers), the system should reject the registration.
**Validates: Requirements 1.3**

### Property 5: Duplicate transaction prevention
*For any* CSV import containing duplicate transactions (same transaction_id), the system should skip the duplicate entries and not create duplicate records.
**Validates: Requirements 5.3**

### Property 6: Request validation
*For any* API request with missing required fields, the system should return a 400 Bad Request error with details about the missing fields.
**Validates: Requirements 13.2**

### Property 7: User ID association
*For any* transaction created through the API, the transaction should be automatically associated with the authenticated user's ID.
**Validates: Requirements 9.1**

### Property 8: Token refresh validity
*For any* valid refresh token, the system should issue a new access token with the same user identity.
**Validates: Requirements 2.4**

### Property 9: Error response standardization
*For any* error condition, the system should return a response containing an error code and human-readable message.
**Validates: Requirements 10.2**

### Property 10: HTTPS enforcement
*For any* HTTP request to the API, the system should redirect to HTTPS or reject the request.
**Validates: Requirements 11.2**

### Property 11: Date range filtering
*For any* transaction query with start and end date filters, all returned transactions should have transaction dates within the specified range (inclusive).
**Validates: Requirements 4.2**

### Property 12: Amount range filtering
*For any* transaction query with minimum and maximum amount filters, all returned transactions should have amounts within the specified range.
**Validates: Requirements 4.4**


## Error Handling

### Error Response Format
All errors will follow a consistent JSON structure:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "Additional context"
    }
  }
}
```

### HTTP Status Codes
- **200 OK**: Successful request
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid input or validation error
- **401 Unauthorized**: Missing or invalid authentication
- **403 Forbidden**: Authenticated but not authorized
- **404 Not Found**: Resource does not exist
- **409 Conflict**: Resource conflict (e.g., duplicate email)
- **422 Unprocessable Entity**: Semantic validation error
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Unexpected server error
- **503 Service Unavailable**: Service temporarily unavailable

### Error Codes
- `AUTH_INVALID_CREDENTIALS`: Invalid email or password
- `AUTH_TOKEN_EXPIRED`: JWT token has expired
- `AUTH_TOKEN_INVALID`: JWT token is malformed or invalid
- `AUTH_EMAIL_EXISTS`: Email already registered
- `AUTH_USER_NOT_FOUND`: User does not exist
- `VALIDATION_ERROR`: Input validation failed
- `RESOURCE_NOT_FOUND`: Requested resource not found
- `PERMISSION_DENIED`: User lacks permission for resource
- `IMPORT_INVALID_FORMAT`: CSV format is invalid
- `DATABASE_ERROR`: Database operation failed
- `RATE_LIMIT_EXCEEDED`: Too many requests

### Exception Handling Strategy
1. **Validation Errors**: Caught by Pydantic, return 400 with field details
2. **Authentication Errors**: Caught by middleware, return 401
3. **Authorization Errors**: Caught by service layer, return 403
4. **Database Errors**: Caught by repository layer, logged and return 500
5. **Cognito Errors**: Caught by auth service, mapped to appropriate HTTP status
6. **Unhandled Exceptions**: Caught by global handler, logged with trace, return 500


## Testing Strategy

### Unit Testing
Unit tests will verify individual components in isolation:
- **Pydantic Models**: Validate serialization/deserialization
- **Service Layer**: Test business logic with mocked repositories
- **Repository Layer**: Test database operations with test database
- **Utilities**: Test JWT validation, date parsing, etc.
- **Middleware**: Test authentication and logging logic

**Framework**: pytest with pytest-asyncio for async tests

**Coverage Target**: 80% minimum code coverage

### Property-Based Testing
Property-based tests will verify universal properties across many inputs:
- **Library**: Hypothesis for Python
- **Configuration**: Minimum 100 iterations per property test
- **Tagging**: Each test tagged with format: `# Feature: api-authentication, Property {number}: {property_text}`

Property tests will cover:
- User data isolation across random user IDs and transaction sets
- JWT validation with various token formats and expiration times
- Request validation with randomly generated invalid inputs
- Date and amount filtering with random ranges
- Duplicate detection with random transaction sets

### Integration Testing
Integration tests will verify component interactions:
- **API Endpoints**: Test full request/response cycle
- **Database Operations**: Test actual database queries
- **Cognito Integration**: Test against Cognito test environment
- **Authentication Flow**: Test end-to-end login/logout
- **CSV Import**: Test with sample CSV files

**Tools**: 
- pytest with httpx for API testing
- TestContainers for PostgreSQL test database
- Moto for AWS service mocking (Cognito)

### End-to-End Testing
E2E tests will verify complete user workflows:
- User registration → email verification → login
- Login → query transactions → logout
- Login → import CSV → verify transactions → query analytics
- Password reset flow

**Tools**: pytest with httpx for API calls

### Test Data Management
- **Fixtures**: pytest fixtures for common test data
- **Factories**: Factory pattern for generating test objects
- **Database**: Separate test database, reset between tests
- **Cognito**: Use Cognito test user pool or mocked service


## Database Migration Strategy

### Phase 1: Add User Support
1. Create `users` table in PostgreSQL
2. Create `import_history` table in PostgreSQL
3. Add `user_id` column to existing transaction tables (nullable initially)
4. Create indexes on `user_id` columns

### Phase 2: Data Migration
1. Create a "system" user for existing data
2. Update all existing transactions to reference system user
3. Make `user_id` column NOT NULL
4. Add foreign key constraints

### Phase 3: Dual-Write Period
1. New transactions written to both Snowflake and PostgreSQL
2. Validate data consistency
3. Monitor performance

### Phase 4: PostgreSQL Primary (Optional)
1. Switch reads to PostgreSQL
2. Keep Snowflake for analytics/backup
3. Eventually deprecate Snowflake if desired

### Schema Changes

**New Tables (PostgreSQL):**
```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_sub VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE import_history (
    import_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    import_type VARCHAR(50) NOT NULL,
    account_id VARCHAR(100) NOT NULL,
    filename VARCHAR(255),
    rows_total INTEGER NOT NULL,
    rows_inserted INTEGER NOT NULL,
    rows_skipped INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_import_history_user_id ON import_history(user_id);
CREATE INDEX idx_import_history_created_at ON import_history(created_at);
```

**Modified Tables:**
```sql
-- Add to existing CC_TRANSACTIONS
ALTER TABLE cc_transactions ADD COLUMN user_id UUID;
CREATE INDEX idx_cc_transactions_user_id ON cc_transactions(user_id);

-- Add to existing BANK_TRANSACTIONS  
ALTER TABLE bank_transactions ADD COLUMN user_id UUID;
CREATE INDEX idx_bank_transactions_user_id ON bank_transactions(user_id);
```


## Security Considerations

### Authentication Security
- **Password Storage**: Managed by Cognito (bcrypt with salt)
- **Token Security**: JWT tokens signed with RS256 algorithm
- **Token Expiration**: Access tokens expire after 1 hour
- **Refresh Tokens**: Valid for 30 days, rotated on use
- **Token Storage**: Client-side in httpOnly cookies (recommended) or localStorage

### API Security
- **HTTPS Only**: All traffic encrypted with TLS 1.2+
- **CORS**: Restricted to approved origins
- **Rate Limiting**: 100 requests per minute per user
- **Input Validation**: All inputs validated with Pydantic
- **SQL Injection**: Prevented by parameterized queries
- **XSS Prevention**: API returns JSON only, no HTML rendering

### Data Security
- **Data Isolation**: User ID filtering on all queries
- **Encryption at Rest**: Database encryption enabled
- **Encryption in Transit**: TLS for all connections
- **Sensitive Data**: Passwords never logged or stored in API
- **PII Protection**: Email addresses treated as sensitive

### AWS Cognito Configuration
- **Password Policy**: 
  - Minimum 8 characters
  - Require uppercase, lowercase, numbers
  - Optional: special characters
- **MFA**: Optional, can be enabled per user
- **Account Recovery**: Email-based password reset
- **Email Verification**: Required for new accounts
- **User Pool**: Separate pools for dev/staging/production

### Security Headers
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
```

## Deployment Architecture

### Development Environment
- Local FastAPI server with hot reload
- Local PostgreSQL in Docker
- Cognito test user pool
- Mock Snowflake or local test database

### Staging Environment
- AWS ECS Fargate (1 task)
- AWS RDS PostgreSQL (db.t3.micro)
- AWS Cognito User Pool (staging)
- Snowflake (shared with production)
- AWS Application Load Balancer
- AWS CloudWatch for logs

### Production Environment
- AWS ECS Fargate (2+ tasks with auto-scaling)
- AWS RDS PostgreSQL (db.t3.medium with Multi-AZ)
- AWS Cognito User Pool (production)
- Snowflake (production instance)
- AWS Application Load Balancer with SSL
- AWS CloudWatch for logs and metrics
- AWS CloudWatch Alarms for monitoring

### Infrastructure as Code
Use Terraform to define:
- VPC and networking
- ECS cluster and services
- RDS database instances
- Cognito user pools
- Load balancers and target groups
- Security groups and IAM roles
- CloudWatch log groups and alarms

