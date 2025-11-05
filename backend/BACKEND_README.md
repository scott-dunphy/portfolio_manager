# Portfolio Manager Backend

## Quick Start

### Method 1: Using the Startup Script (Recommended)

```bash
cd backend
./start_backend.sh
```

### Method 2: Manual Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install requirements:
```bash
pip install -r requirements.txt
```

4. Initialize the database (first time only):
```bash
python3 -c "from app import app, db; app.app_context().push(); db.create_all()"
```

5. Start the server:
```bash
python3 app.py
```

The backend will start on `http://localhost:5000`

## API Endpoints

- `GET /health` - Health check endpoint
- `GET /api/portfolios` - List all portfolios
- `POST /api/portfolios` - Create a new portfolio
- `GET /api/portfolios/:id` - Get portfolio details
- `PUT /api/portfolios/:id` - Update portfolio
- `DELETE /api/portfolios/:id` - Delete portfolio

## Troubleshooting

### Port Already in Use
If you see an error that port 5000 is already in use:
```bash
# Find the process using port 5000
lsof -i :5000

# Kill the process (replace PID with actual process ID)
kill -9 PID
```

### Database Issues
If you encounter database errors, try recreating the database:
```bash
rm portfolio_manager.db
python3 -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### CORS Issues
CORS is already configured in the app. If you still encounter CORS issues, check that the frontend is making requests to `http://localhost:5000/api`

## Development

The backend uses:
- Flask for the web framework
- SQLAlchemy for database ORM
- Flask-CORS for cross-origin requests
- SQLite for the database
