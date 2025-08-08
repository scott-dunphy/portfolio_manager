# Portfolio Manager

## Frontend

A React single-page application lives in `frontend/`.

### Build steps

```
cd frontend
npm install
npm run build
```

This generates static assets in `frontend/dist` served by the backend.

## Backend

Install dependencies and run the server:

```
pip install -r requirements.txt
uvicorn main:app --reload
```

The server exposes `/upload` for file uploads and `/api/*` endpoints for portfolios, properties, and loans.
