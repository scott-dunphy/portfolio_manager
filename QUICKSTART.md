# Quick Start Guide

This guide will help you get the Portfolio Manager application running quickly.

## Prerequisites Check

Before starting, make sure you have:
- Python 3.8+ installed: `python --version` or `python3 --version`
- Node.js 16+ installed: `node --version`
- npm installed: `npm --version`

## Step 1: Start the Backend

Open a terminal and run:

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Mac/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
python app.py
```

You should see:
```
Database tables created successfully!
Server running at http://localhost:5000
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
```

**Keep this terminal open!** The backend must keep running.

## Step 2: Test the Backend (Optional)

Open a NEW terminal and run:

```bash
cd backend
python test_api.py
```

This will verify the backend is working correctly.

## Step 3: Start the Frontend

Open another NEW terminal and run:

```bash
cd frontend

# Install dependencies (only needed first time)
npm install

# Start the frontend
npm run dev
```

You should see:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3000/
```

## Step 4: Open the Application

Open your web browser and go to:
```
http://localhost:3000
```

## Troubleshooting

### Problem: "Nothing happens when I click Create"

**Solution 1**: Make sure you fill in ALL required fields:
- Portfolio Name (required)
- Start Date (required)
- End Date (required)

**Solution 2**: Check if the backend is running:
1. Open http://localhost:5000/health in your browser
2. You should see: `{"status":"healthy"}`
3. If you see an error or can't connect, restart the backend (see Step 1)

**Solution 3**: Check browser console for errors:
1. Press F12 in your browser
2. Click the "Console" tab
3. Look for any red error messages
4. Common errors:
   - "Network Error" or "Failed to fetch" → Backend is not running
   - "CORS error" → Backend CORS configuration issue

### Problem: "ModuleNotFoundError" in backend

**Solution**: Make sure you activated the virtual environment:
```bash
cd backend
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate  # Windows
```

### Problem: Frontend shows blank page

**Solution**:
1. Check browser console (F12) for errors
2. Make sure you're on http://localhost:3000 (not 5000)
3. Try refreshing the page (Ctrl+R or Cmd+R)

### Problem: Port already in use

**Backend (port 5000)**:
```bash
# Mac/Linux
lsof -ti:5000 | xargs kill

# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

**Frontend (port 3000)**:
```bash
# Mac/Linux
lsof -ti:3000 | xargs kill

# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

## Testing the Application

### Create Your First Portfolio

1. Click "New Portfolio" button
2. Fill in:
   - Name: "My First Portfolio"
   - Start Date: Today's date
   - End Date: One year from today
   - Leave other fields as default (zeros are fine)
3. Click "Create"
4. You should see your portfolio appear as a card

### Add a Property

1. Click "View Details" on your portfolio
2. Click "Add Property" button
3. Fill in the required fields:
   - Property ID: "PROP-001"
   - Property Name: "123 Main Street"
4. Click "Create Property"

### Upload Excel Data

1. Click "Upload Excel" button from main page
2. Click "Download Template" to get the Excel format
3. Fill in the template with your data
4. Select your portfolio
5. Drag and drop the file or click to select it
6. Click "Upload File"

## Next Steps

Once everything is working:
- Explore the property and loan management features
- Try editing and deleting items
- Import bulk data using the Excel template
- Check out the Portfolio Detail view for a complete overview

## Getting Help

If you're still having issues:
1. Check that both backend (port 5000) and frontend (port 3000) are running
2. Look at the terminal where the backend is running for error messages
3. Check the browser console (F12) for frontend errors
4. Make sure all required fields are filled when creating items
