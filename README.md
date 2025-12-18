# FinApp - The Personal Finance Tracker

A modern personal finance tracking application with a React frontend and FastAPI backend, featuring multi-user authentication via AWS Cognito.

## 🚀 Features

### Dashboard
- **Overview** - Quick summary with spending charts and income vs expenses comparison
- **Transactions** - Filterable transaction list with search, date range, category, and account filters
- **Year to Date** - YTD spending analysis with net cash flow calculations
- **Monthly** - Month-by-month spending breakdown and comparisons
- **Categories** - Spending by category with pie charts and uncategorized transaction analysis
- **Housing** - Dedicated view for mortgage, utilities, insurance, and home maintenance expenses
- **Trends** - Spending trends over the last 12 months
- **Data Validation** - Diagnostic tools for verifying data accuracy and detecting duplicates
- **API Health** - Real-time monitoring of API, database, and Cognito connectivity

### Core Functionality
- 🔐 **Multi-user authentication** with AWS Cognito
- 📊 **Interactive charts** using Chart.js (line, bar, pie charts)
- 🌙 **Dark mode** with system preference detection
- 📱 **Responsive design** with Tailwind CSS
- 📥 **CSV import** for credit cards and bank statements (multiple formats supported)
- 🔍 **Advanced filtering** by date, category, account, description, and amount
- 💰 **Financial metrics** including YTD spending, daily averages, and projections

## 🏗️ Architecture

```
finapp/
├── api/                    # FastAPI Backend
│   ├── routers/           # API endpoints (auth, transactions, imports, health)
│   ├── services/          # Business logic
│   ├── repositories/      # Data access layer
│   ├── models/            # Pydantic & SQLAlchemy models
│   ├── middleware/        # Auth, error handling, logging
│   └── alembic/           # Database migrations
├── frontend/              # React + TypeScript Frontend
│   ├── src/
│   │   ├── pages/         # Page components (Dashboard, Login, Import, etc.)
│   │   ├── components/    # Reusable components
│   │   ├── contexts/      # React contexts (Auth, Theme)
│   │   └── lib/           # API client and utilities
│   └── vite.config.ts     # Vite configuration with proxy
├── infrastructure/        # Terraform for AWS resources
├── application/           # Legacy Flask application (deprecated)
└── docs/                  # Documentation
```

## 🛠️ Tech Stack

### Backend (FastAPI)
| Technology | Purpose |
|------------|---------|
| FastAPI | REST API framework with automatic OpenAPI docs |
| PostgreSQL | Primary database |
| SQLAlchemy 2.0 | Async ORM with type hints |
| Alembic | Database migrations |
| AWS Cognito | User authentication |
| Pydantic | Data validation |
| boto3 | AWS SDK for Cognito integration |

### Frontend (React)
| Technology | Purpose |
|------------|---------|
| React 18 | UI framework |
| TypeScript | Type safety |
| Vite | Build tool and dev server |
| Tailwind CSS | Utility-first styling |
| Chart.js | Data visualization |
| React Router | Client-side routing |
| Axios | HTTP client with interceptors |
| date-fns | Date manipulation |

## 📋 Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.11+
- **PostgreSQL** 15+ (or Docker)
- **AWS Account** with Cognito User Pool configured

## 🚀 Quick Start

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone https://github.com/your-username/finapp.git
cd finapp

# Copy environment files
cp api/.env.example api/.env
```

### 2. Configure AWS Cognito

Edit `api/.env` with your Cognito credentials:

```env
DATABASE_URL=postgresql+asyncpg://finapp:finapp@localhost:5432/finapp
COGNITO_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_APP_CLIENT_ID=your-client-id
COGNITO_APP_CLIENT_SECRET=your-client-secret
```

### 3. Start the Backend

```bash
# Terminal 1: Start PostgreSQL
cd api
docker-compose up -d postgres

# Run database migrations
pip install -r requirements.txt
alembic upgrade head

# Start the API server (from project root!)
cd ..
uvicorn api.main:app --reload --port 8000
```

> ⚠️ **Important:** Run `uvicorn` from the project root directory, not from inside `api/`.

Verify the API is running: http://localhost:8000/api/v1/health

### 4. Start the Frontend

```bash
# Terminal 2: Start the frontend
cd frontend
npm install
npm run dev
```

The app will be available at: http://localhost:3000

## 📚 API Documentation

Once the backend is running, access interactive API docs:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | Register new user |
| `/api/v1/auth/login` | POST | Login and get tokens |
| `/api/v1/auth/refresh` | POST | Refresh access token |
| `/api/v1/transactions` | GET | List transactions with filters |
| `/api/v1/imports/credit-card` | POST | Import credit card CSV |
| `/api/v1/imports/bank` | POST | Import bank statement CSV |
| `/api/v1/health` | GET | Health check |
| `/api/v1/health/ready` | GET | Readiness check (DB + Cognito) |

## 📥 Importing Data

### Supported CSV Formats

**Credit Card Formats:**
1. **Standard** - Transaction Date, Post Date, Description, Category, Type, Amount, Memo
2. **Apple Card** - Transaction Date, Clearing Date, Description, Merchant, Category, Type, Amount
3. **Amex** - Date, Description, Amount, Category
4. **Capital One** - Transaction Date, Posted Date, Card No., Description, Category, Debit, Credit

**Bank Statement Format:**
- Posted Date, Effective Date, Description, Transaction Type, Amount, Balance, Check Number, Memo

### Import Process

1. Navigate to the **Import** page from the dashboard
2. Select **Credit Card** or **Bank Statement** tab
3. Choose your CSV file
4. Enter an account ID (e.g., `cc_chase`, `cc_apple`, `chk_main`)
5. Click **Import**

## 🧪 Development

### Running Tests

```bash
cd api
pytest
```

### Creating Database Migrations

```bash
cd api
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

### Building for Production

```bash
# Frontend
cd frontend
npm run build

# The built files will be in frontend/dist/
```

## 📁 Project Structure Details

### Backend (`api/`)

```
api/
├── main.py                 # FastAPI application entry point
├── config.py              # Settings from environment variables
├── dependencies.py        # Dependency injection (services, repos)
├── routers/
│   ├── auth.py            # Authentication endpoints
│   ├── transactions.py    # Transaction CRUD
│   ├── imports.py         # CSV import endpoints
│   ├── analytics.py       # Dashboard metrics
│   └── health.py          # Health checks
├── services/
│   ├── auth_service.py    # Cognito integration
│   ├── transaction_service.py
│   ├── import_service.py  # CSV parsing logic
│   └── analytics_service.py
├── repositories/
│   ├── transaction_repository.py
│   ├── user_repository.py
│   └── import_repository.py
├── models/
│   ├── domain.py          # SQLAlchemy models
│   ├── requests.py        # Pydantic request models
│   └── responses.py       # Pydantic response models
└── alembic/
    └── versions/          # Migration files
```

### Frontend (`frontend/`)

```
frontend/
├── src/
│   ├── App.tsx            # Routes and providers
│   ├── main.tsx           # Entry point
│   ├── index.css          # Global styles (Tailwind)
│   ├── pages/
│   │   ├── Dashboard.tsx  # Main dashboard with tabs
│   │   ├── Login.tsx
│   │   ├── Register.tsx
│   │   ├── ForgotPassword.tsx
│   │   └── Import.tsx     # CSV upload interface
│   ├── components/
│   │   └── ProtectedRoute.tsx
│   ├── contexts/
│   │   ├── AuthContext.tsx   # Authentication state
│   │   └── ThemeContext.tsx  # Dark mode state
│   └── lib/
│       └── api.ts         # Axios client with interceptors
├── vite.config.ts         # Proxy config for API
└── tailwind.config.js     # Dark mode enabled
```

## 🔒 Security

- **JWT Authentication** via AWS Cognito (RS256)
- **Password hashing** managed by Cognito (bcrypt with salt)
- **HTTPS** enforced in production
- **CORS** configured for frontend origin
- **SQL injection prevention** with parameterized queries
- **Input validation** with Pydantic models
- **Token refresh** handled automatically by frontend

## 🎨 Theming

The app supports light and dark modes:
- Respects system preferences by default
- Toggle available in the dashboard header
- Preference persisted to localStorage
- Smooth transitions between themes

## 📊 Dashboard Tabs

| Tab | Description |
|-----|-------------|
| **Overview** | Summary cards, spending trends, income vs expenses chart |
| **Transactions** | Searchable/filterable transaction table |
| **Year to Date** | YTD metrics, net cash flow analysis |
| **Monthly** | Month-by-month comparison, averages |
| **Categories** | Spending by category, uncategorized analysis |
| **Housing** | Mortgage, utilities, insurance, maintenance tracking |
| **Trends** | 12-month spending trend with projections |
| **Data Validation** | Duplicate detection, data integrity checks |
| **API Health** | Service status monitoring |

## 🗄️ Legacy Application

The `application/` directory contains a legacy Flask application that uses Snowflake. This is deprecated and kept for reference. The new architecture uses:
- **FastAPI** instead of Flask
- **PostgreSQL** instead of Snowflake
- **AWS Cognito** instead of no authentication
- **React** instead of server-rendered templates

## 📖 Additional Documentation

- [API README](api/README.md) - Detailed API documentation
- [Frontend README](frontend/README.md) - Frontend setup and development
- [Infrastructure README](infrastructure/README.md) - Terraform/AWS setup
- [Overview](docs/OVERVIEW.md) - Legacy application documentation

## 📄 License

See [LICENSE](LICENSE) file.

---

Built with ❤️ using FastAPI, React, and TypeScript
