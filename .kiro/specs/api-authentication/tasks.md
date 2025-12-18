# Implementation Plan

## Overview
This implementation plan breaks down the API and authentication modernization into incremental, testable tasks. Each task builds on previous work and includes references to the requirements being implemented.

- [x] 1. Set up project infrastructure and AWS Cognito
  - Create FastAPI project structure with proper directory organization
  - Set up AWS Cognito User Pool with password policies and email verification
  - Configure development environment with local PostgreSQL
  - Set up configuration management for environment-specific settings
  - _Requirements: 1.1, 1.3, 2.1, 11.1_

- [x] 1.1 Create FastAPI project structure
  - Create directory structure (routers, services, repositories, models, middleware, utils)
  - Set up main.py with FastAPI application initialization
  - Create config.py for environment variable management
  - Set up dependencies.py for dependency injection
  - _Requirements: 8.1, 8.2_

- [x] 1.2 Set up AWS Cognito User Pool
  - Create Cognito User Pool via AWS Console or Terraform
  - Configure password policy (8 chars, uppercase, lowercase, numbers)
  - Enable email verification for new accounts
  - Configure email templates for verification and password reset
  - Create app client for API integration
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 3.1_

- [x] 1.3 Set up local development database
  - Create Docker Compose file for PostgreSQL
  - Create initial database schema (users table)
  - Set up database connection utilities
  - Create Alembic configuration for migrations
  - _Requirements: 9.1, 12.4_

- [x] 1.4 Create configuration management
  - Implement config.py with Pydantic settings
  - Load environment variables for database, Cognito, API settings
  - Create separate configs for dev/staging/production
  - Add validation for required configuration values
  - _Requirements: 14.5_


- [x] 2. Implement authentication service and JWT middleware
  - Create Cognito integration service for user operations
  - Implement JWT token validation middleware
  - Create authentication utilities for token handling
  - Build user service for user management
  - _Requirements: 2.1, 2.2, 2.3, 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 2.1 Create Cognito authentication service
  - Implement register_user method with Cognito SignUp
  - Implement login method with Cognito InitiateAuth
  - Implement refresh_token method
  - Implement forgot_password and reset_password methods
  - Handle Cognito exceptions and map to application errors
  - _Requirements: 1.1, 2.1, 2.4, 3.1, 3.2_

- [x] 2.2 Implement JWT validation middleware
  - Fetch Cognito public keys (JWKS)
  - Validate JWT signature using public keys
  - Check token expiration
  - Extract user_id (sub) from token claims
  - Inject user_id into request context
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 2.3 Write property test for JWT validation
  - **Property 2: JWT token validation**
  - **Validates: Requirements 7.2, 7.3, 7.5**

- [x] 2.4 Create user repository and service
  - Implement user repository with database operations
  - Create user on first login (sync with Cognito)
  - Implement get_user_by_cognito_sub method
  - Implement get_user_by_email method
  - _Requirements: 9.1, 9.5_

- [x] 2.5 Write property test for user data isolation
  - **Property 1: User data isolation**
  - **Validates: Requirements 9.2**

- [x] 3. Implement authentication API endpoints
  - Create authentication router with register, login, refresh, logout endpoints
  - Implement request/response models for authentication
  - Add error handling for authentication failures
  - Create health check endpoints
  - _Requirements: 1.1, 1.5, 2.1, 2.2, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3.1 Create authentication router
  - Implement POST /api/v1/auth/register endpoint
  - Implement POST /api/v1/auth/login endpoint
  - Implement POST /api/v1/auth/refresh endpoint
  - Implement POST /api/v1/auth/logout endpoint
  - Implement POST /api/v1/auth/forgot-password endpoint
  - Implement POST /api/v1/auth/reset-password endpoint
  - Implement GET /api/v1/auth/me endpoint
  - _Requirements: 1.1, 2.1, 2.5, 3.1, 3.2_

- [x] 3.2 Create authentication request/response models
  - Define RegisterRequest with email and password validation
  - Define LoginRequest with email and password
  - Define TokenResponse with access_token, refresh_token, expires_in
  - Define RefreshTokenRequest
  - Define ForgotPasswordRequest and ResetPasswordRequest
  - Define UserResponse for /auth/me endpoint
  - _Requirements: 1.3, 13.1, 13.2, 13.3, 13.4_

- [x] 3.3 Write property test for password requirements
  - **Property 4: Password requirement enforcement**
  - **Validates: Requirements 1.3**

- [x] 3.4 Write property test for authentication token generation
  - **Property 3: Authentication token generation**
  - **Validates: Requirements 2.1, 2.3**

- [x] 3.5 Write property test for token refresh
  - **Property 8: Token refresh validity**
  - **Validates: Requirements 2.4**

- [x] 3.6 Create health check endpoints
  - Implement GET /api/v1/health endpoint
  - Implement GET /api/v1/health/ready endpoint
  - Check database connectivity
  - Check Cognito connectivity
  - _Requirements: 14.5_


- [x] 4. Implement database schema changes for multi-user support
  - Create database migration for users table
  - Add user_id column to transaction tables
  - Create import_history table
  - Create indexes for performance
  - Migrate existing data to system user
  - _Requirements: 9.1, 9.2, 9.4, 9.5, 12.4_

- [x] 4.1 Create users table migration
  - Create Alembic migration for users table
  - Add columns: user_id, cognito_sub, email, created_at, updated_at, is_active
  - Add unique constraints on cognito_sub and email
  - Add indexes on email and cognito_sub
  - _Requirements: 9.1_

- [x] 4.2 Add user_id to transaction tables
  - Create migration to add user_id column (nullable initially)
  - Add user_id to cc_transactions table
  - Add user_id to bank_transactions table
  - Create indexes on user_id columns
  - _Requirements: 9.1, 9.2_

- [x] 4.3 Create import_history table
  - Create migration for import_history table
  - Add columns: import_id, user_id, import_type, account_id, filename, rows_total, rows_inserted, rows_skipped, status, error_message, created_at
  - Add foreign key to users table
  - Add indexes on user_id and created_at
  - _Requirements: 5.4_

- [x] 4.4 Migrate existing transaction data
  - Create system user in users table
  - Update all existing transactions to reference system user
  - Make user_id column NOT NULL
  - Add foreign key constraints
  - _Requirements: 9.4, 12.4_

- [x] 5. Implement transaction API endpoints
  - Create transaction repository with user filtering
  - Create transaction service with business logic
  - Implement transaction router with CRUD endpoints
  - Add request/response models for transactions
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 9.2, 9.3_

- [x] 5.1 Create transaction repository
  - Implement get_transactions with user_id filtering
  - Implement get_transaction_by_id with user_id check
  - Implement create_transaction with user_id
  - Implement update_transaction with user_id check
  - Implement delete_transaction with user_id check
  - Add support for date range, description, category, amount filters
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 9.2_

- [x] 5.2 Write property test for date range filtering
  - **Property 11: Date range filtering**
  - **Validates: Requirements 4.2**

- [x] 5.3 Write property test for amount range filtering
  - **Property 12: Amount range filtering**
  - **Validates: Requirements 4.4**

- [x] 5.4 Create transaction service
  - Implement get_transactions with filter logic
  - Implement get_transaction with authorization check
  - Implement create_transaction with validation
  - Implement update_transaction with authorization
  - Implement delete_transaction with authorization
  - _Requirements: 4.1, 9.2, 9.3_

- [x] 5.5 Create transaction router
  - Implement GET /api/v1/transactions endpoint with filters
  - Implement GET /api/v1/transactions/{id} endpoint
  - Implement POST /api/v1/transactions endpoint
  - Implement PUT /api/v1/transactions/{id} endpoint
  - Implement DELETE /api/v1/transactions/{id} endpoint
  - Add authentication middleware to all endpoints
  - _Requirements: 4.1, 4.5, 7.5_

- [x] 5.6 Create transaction request/response models
  - Define TransactionResponse with all transaction fields
  - Define CreateTransactionRequest with validation
  - Define UpdateTransactionRequest with validation
  - Define TransactionListResponse with pagination
  - Define TransactionFilters for query parameters
  - _Requirements: 13.1, 13.2, 13.3, 13.4_

- [x] 5.7 Write property test for user ID association
  - **Property 7: User ID association**
  - **Validates: Requirements 9.1**


- [ ] 6. Implement CSV import API endpoints
  - Migrate existing CSV parsing logic to service layer
  - Create import service with user association
  - Implement import router with credit card and bank endpoints
  - Add import history tracking
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 6.1 Refactor CSV parsing logic
  - Extract CSV parsing from existing ingest scripts
  - Create reusable CSV parser for credit card transactions
  - Create reusable CSV parser for bank transactions
  - Add format detection and validation
  - Handle multiple CSV formats (standard, Apple Card, Amex)
  - _Requirements: 5.2_

- [ ] 6.2 Create import service
  - Implement import_credit_card_csv method
  - Implement import_bank_csv method
  - Associate imported transactions with user_id
  - Generate deterministic transaction IDs
  - Skip duplicate transactions
  - Track import history
  - _Requirements: 5.1, 5.3, 5.4_

- [ ] 6.3 Write property test for duplicate prevention
  - **Property 5: Duplicate transaction prevention**
  - **Validates: Requirements 5.3**

- [ ] 6.4 Create import router
  - Implement POST /api/v1/imports/credit-card endpoint
  - Implement POST /api/v1/imports/bank endpoint
  - Implement GET /api/v1/imports/history endpoint
  - Implement GET /api/v1/imports/{id} endpoint
  - Handle file uploads with multipart/form-data
  - Add authentication middleware
  - _Requirements: 5.1, 5.5_

- [ ] 6.5 Create import request/response models
  - Define ImportRequest with file and account_id
  - Define ImportResponse with summary statistics
  - Define ImportHistoryResponse
  - Add validation for file types and sizes
  - _Requirements: 5.4, 13.1, 13.2_

- [ ] 7. Implement analytics API endpoints
  - Create analytics service for dashboard metrics
  - Migrate existing metrics computation logic
  - Implement analytics router with dashboard, spending, trends endpoints
  - Add user-specific filtering to all analytics
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 7.1 Create analytics service
  - Implement compute_dashboard_metrics with user_id filtering
  - Implement get_spending_by_category with user_id filtering
  - Implement get_spending_trends with user_id filtering
  - Implement build_correlated_payments with user_id filtering
  - Migrate logic from existing metrics.py
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 7.2 Create analytics router
  - Implement GET /api/v1/analytics/dashboard endpoint
  - Implement GET /api/v1/analytics/spending endpoint
  - Implement GET /api/v1/analytics/trends endpoint
  - Implement GET /api/v1/analytics/correlations endpoint
  - Add authentication middleware
  - Add date range parameters
  - _Requirements: 6.1, 6.5_

- [ ] 7.3 Create analytics response models
  - Define DashboardMetricsResponse
  - Define SpendingByCategoryResponse
  - Define SpendingTrendsResponse
  - Define CorrelatedPaymentsResponse
  - Define DailySpending and CategorySpending models
  - _Requirements: 6.2, 6.3, 6.4_

- [ ] 8. Implement error handling and logging
  - Create global exception handler
  - Implement standardized error responses
  - Add request/response logging middleware
  - Configure structured logging
  - Add error tracking
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 14.1, 14.2, 14.3, 14.4_

- [ ] 8.1 Create global exception handler
  - Handle validation errors (Pydantic)
  - Handle authentication errors
  - Handle authorization errors (403)
  - Handle database errors
  - Handle Cognito errors
  - Handle unhandled exceptions
  - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [ ] 8.2 Write property test for error response format
  - **Property 9: Error response standardization**
  - **Validates: Requirements 10.2**

- [ ] 8.3 Create logging middleware
  - Log all incoming requests (method, path, user_id, timestamp)
  - Log all responses (status code, duration)
  - Log authentication failures
  - Log slow database queries (>1 second)
  - Exclude sensitive data from logs
  - _Requirements: 14.1, 14.2, 14.3, 14.4, 11.4_

- [ ] 8.4 Configure structured logging
  - Set up JSON logging format
  - Configure log levels per environment
  - Add correlation IDs for request tracing
  - Configure log rotation
  - _Requirements: 14.1, 14.5_


- [ ] 9. Implement security features
  - Add HTTPS enforcement
  - Configure CORS policies
  - Add security headers
  - Implement rate limiting
  - Add input sanitization
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 10.5_

- [ ] 9.1 Configure HTTPS and security headers
  - Add HTTPS redirect middleware
  - Add Strict-Transport-Security header
  - Add X-Content-Type-Options header
  - Add X-Frame-Options header
  - Add Content-Security-Policy header
  - _Requirements: 11.1, 11.2, 11.3_

- [ ] 9.2 Write property test for HTTPS enforcement
  - **Property 10: HTTPS enforcement**
  - **Validates: Requirements 11.2**

- [ ] 9.3 Configure CORS
  - Define allowed origins per environment
  - Set allowed methods (GET, POST, PUT, DELETE)
  - Set allowed headers (Authorization, Content-Type)
  - Configure credentials support
  - _Requirements: 11.5_

- [ ] 9.4 Implement rate limiting
  - Add rate limiting middleware (100 requests/minute per user)
  - Track requests by user_id or IP address
  - Return 429 error when limit exceeded
  - Add rate limit headers to responses
  - _Requirements: 10.5_

- [ ] 9.5 Add input sanitization
  - Validate all string inputs for length
  - Sanitize file uploads
  - Validate email formats
  - Validate date formats
  - _Requirements: 13.1, 13.2, 13.3, 13.4_

- [ ] 9.6 Write property test for request validation
  - **Property 6: Request validation**
  - **Validates: Requirements 13.2**

- [ ] 10. Create API documentation
  - Configure OpenAPI/Swagger documentation
  - Add endpoint descriptions and examples
  - Document authentication requirements
  - Add response schemas
  - Create API usage guide
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 10.1 Configure OpenAPI documentation
  - Set up FastAPI automatic documentation
  - Configure Swagger UI at /docs
  - Configure ReDoc at /redoc
  - Add API metadata (title, version, description)
  - _Requirements: 8.1, 8.2_

- [ ] 10.2 Add endpoint documentation
  - Add docstrings to all endpoint functions
  - Add request/response examples
  - Document query parameters
  - Document path parameters
  - Document request bodies
  - _Requirements: 8.3_

- [ ] 10.3 Document authentication
  - Add security scheme for JWT Bearer tokens
  - Mark protected endpoints with security requirements
  - Add authentication flow documentation
  - Document token refresh process
  - _Requirements: 8.4_

- [ ] 10.4 Document error responses
  - Add error response schemas to endpoints
  - Document all possible error codes
  - Add error response examples
  - Create error code reference guide
  - _Requirements: 8.5_

- [ ] 11. Set up deployment infrastructure
  - Create Dockerfile for API
  - Create Docker Compose for local development
  - Set up AWS infrastructure with Terraform
  - Configure CI/CD pipeline
  - Set up monitoring and alerting
  - _Requirements: 12.1, 12.2, 12.3, 14.5_

- [ ] 11.1 Create Dockerfile
  - Create multi-stage Dockerfile for FastAPI
  - Optimize image size
  - Add health check
  - Configure non-root user
  - _Requirements: 12.1_

- [ ] 11.2 Create Docker Compose for development
  - Add FastAPI service
  - Add PostgreSQL service
  - Add volume mounts for development
  - Configure networking
  - Add environment variables
  - _Requirements: 12.1, 12.2_

- [ ] 11.3 Create Terraform infrastructure
  - Define VPC and networking
  - Create ECS cluster and task definition
  - Create RDS PostgreSQL instance
  - Create Application Load Balancer
  - Configure security groups
  - Create IAM roles and policies
  - _Requirements: 12.3_

- [ ] 11.4 Set up CI/CD pipeline
  - Create GitHub Actions workflow
  - Add linting and type checking
  - Add automated testing
  - Add Docker image building
  - Add deployment to ECS
  - _Requirements: 12.1_

- [ ] 11.5 Configure monitoring
  - Set up CloudWatch log groups
  - Create CloudWatch dashboards
  - Add performance metrics
  - Create alarms for errors and latency
  - _Requirements: 14.1, 14.2, 14.5_

- [ ] 12. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
