# FinApp Frontend

Modern React + TypeScript frontend for FinApp, connecting to the FastAPI backend.

## Tech Stack

- **React 18** with TypeScript
- **Vite** for build tooling
- **Tailwind CSS** for styling
- **React Router** for routing
- **Axios** for API calls
- **Chart.js** (ready for future charts)

## Setup

### Prerequisites

**IMPORTANT:** The FastAPI backend must be running before starting the frontend!

1. **Start the FastAPI backend** (in a separate terminal):
   ```bash
   # Navigate to the project root (finapp directory)
   cd /path/to/finapp
   
   # Make sure PostgreSQL is running (from api directory)
   cd api
   docker-compose up -d postgres
   
   # Run database migrations (from api directory)
   alembic upgrade head
   
   # Start the API server (from project root, NOT from api directory!)
   cd ..  # Go back to project root
   uvicorn api.main:app --reload --port 8000
   ```
   
   **Important:** The `uvicorn` command must be run from the project root directory (where `api/` is a subdirectory), not from inside the `api/` directory.

   The API should be available at `http://localhost:8000`
   
   Verify it's running by visiting: http://localhost:8000/api/v1/health

2. **Install frontend dependencies**:
   ```bash
   npm install
   ```

3. **Create a `.env` file** (optional, defaults to using Vite proxy):
   ```
   VITE_API_BASE_URL=http://localhost:8000
   ```
   
   Note: If you don't set this, the frontend will use Vite's proxy (recommended for development).

4. **Start the development server**:
   ```bash
   npm run dev
   ```

The app will be available at `http://localhost:3000`

### Troubleshooting

**Connection Refused Error:**
- Make sure the FastAPI backend is running on port 8000
- Check that PostgreSQL is running (if using Docker: `docker-compose ps`)
- Verify the API is accessible: `curl http://localhost:8000/api/v1/health`

## Features

- ✅ User authentication (login, register, forgot password)
- ✅ Protected routes
- ✅ Dashboard with transaction listing
- ✅ Transaction filtering (date range, description, category, amount)
- ✅ Summary cards (total spent, received, net flow)
- ✅ Automatic token refresh
- ✅ Responsive design

## Project Structure

```
frontend/
├── src/
│   ├── components/      # Reusable components
│   ├── contexts/        # React contexts (Auth)
│   ├── lib/            # API client and utilities
│   ├── pages/          # Page components
│   ├── App.tsx         # Main app component with routing
│   └── main.tsx        # Entry point
├── package.json
├── vite.config.ts
└── tailwind.config.js
```

## API Integration

The frontend connects to the FastAPI backend at `/api/v1/*` endpoints:
- `/api/v1/auth/*` - Authentication endpoints
- `/api/v1/transactions` - Transaction endpoints

## Development

- `npm run dev` - Start dev server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Notes

- The legacy Flask application in `../application/` is not modified
- This frontend is completely separate and connects to the new FastAPI backend
- Authentication tokens are stored in localStorage
- Automatic token refresh is handled by axios interceptors

