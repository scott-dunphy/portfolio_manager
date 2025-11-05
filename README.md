# Portfolio Manager

A full-stack web application for managing real estate portfolios, properties, loans, and financial analysis.

## Features

- **Portfolio Management**: Create, edit, and delete portfolios with custom analysis periods
- **Property Management**: Track properties with detailed information including valuations and NOI
- **Loan Management**: Manage loans with principal, interest rates, and payment schedules
- **Preferred Equity**: Track preferred equity investments
- **Excel Import**: Bulk upload properties and loans using Excel templates
- **RESTful API**: Complete backend API for all operations

## Technology Stack

### Backend
- **Flask**: Python web framework
- **SQLAlchemy**: ORM for database operations
- **SQLite**: Database (can be upgraded to PostgreSQL)
- **Pandas**: Excel file processing
- **Flask-CORS**: Cross-origin resource sharing

### Frontend
- **React**: UI framework
- **Vite**: Build tool and dev server
- **Material-UI (MUI)**: Component library
- **React Router**: Client-side routing
- **Axios**: HTTP client
- **React Dropzone**: File upload functionality

## Project Structure

```
portfolio_manager/
├── backend/
│   ├── app.py                 # Flask application
│   ├── database.py            # Database initialization
│   ├── models.py              # SQLAlchemy models
│   ├── requirements.txt       # Python dependencies
│   ├── uploads/               # Excel file uploads directory
│   └── routes/                # API route modules
│       ├── portfolio_routes.py
│       ├── property_routes.py
│       ├── loan_routes.py
│       ├── preferred_equity_routes.py
│       ├── cash_flow_routes.py
│       └── upload_routes.py
├── frontend/
│   ├── src/
│   │   ├── main.jsx           # Application entry point
│   │   ├── App.jsx            # Main app component
│   │   ├── pages/             # Page components
│   │   └── services/          # API service
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── Property_Import_Template.xlsx  # Excel template
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the Flask server:
```bash
python app.py
```

The backend API will be available at `http://localhost:5000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## API Endpoints

### Portfolios
- `GET /api/portfolios` - Get all portfolios
- `GET /api/portfolios/:id` - Get portfolio by ID
- `POST /api/portfolios` - Create new portfolio
- `PUT /api/portfolios/:id` - Update portfolio
- `DELETE /api/portfolios/:id` - Delete portfolio

### Properties
- `GET /api/properties` - Get all properties
- `GET /api/properties/:id` - Get property by ID
- `POST /api/properties` - Create new property
- `PUT /api/properties/:id` - Update property
- `DELETE /api/properties/:id` - Delete property

### Loans
- `GET /api/loans` - Get all loans
- `GET /api/loans/:id` - Get loan by ID
- `POST /api/loans` - Create new loan
- `PUT /api/loans/:id` - Update loan
- `DELETE /api/loans/:id` - Delete loan

### Preferred Equity
- `GET /api/preferred-equities` - Get all preferred equities
- `GET /api/preferred-equities/:id` - Get preferred equity by ID
- `POST /api/preferred-equities` - Create new preferred equity
- `PUT /api/preferred-equities/:id` - Update preferred equity
- `DELETE /api/preferred-equities/:id` - Delete preferred equity

### Cash Flows
- `GET /api/cash-flows` - Get all cash flows
- `GET /api/cash-flows/:id` - Get cash flow by ID
- `POST /api/cash-flows` - Create new cash flow
- `PUT /api/cash-flows/:id` - Update cash flow
- `DELETE /api/cash-flows/:id` - Delete cash flow

### Upload
- `POST /api/upload/excel` - Upload Excel file with properties
- `GET /api/upload/template` - Download Excel template

## Excel Import

To import properties and loans in bulk:

1. Download the Excel template from the Upload page
2. Fill in the property and loan information
3. Select a portfolio to import into
4. Upload the Excel file

The template includes columns for:
- Property information (ID, name, type, address)
- Financial data (purchase price, NOI, cap rates)
- Loan information (principal, interest rate, dates)

## Database Schema

### Portfolio
- id, name, analysis dates, fees, cash, NAV, valuation method

### Property
- id, portfolio_id, property details, financial data, dates

### Loan
- id, portfolio_id, property_id, loan details, rates, dates

### PreferredEquity
- id, portfolio_id, property_id, investment details, returns

### CashFlow
- id, portfolio_id, property_id, loan_id, date, type, amount

## Development

### Building for Production

Frontend:
```bash
cd frontend
npm run build
```

The built files will be in `frontend/dist/`

### Running Tests

Backend tests (to be implemented):
```bash
cd backend
pytest
```

## Future Enhancements

- User authentication and authorization
- Advanced financial analytics and reporting
- Portfolio performance metrics
- Export functionality (Excel, PDF)
- Real-time data synchronization
- Multi-currency support
- Audit logs and history tracking

## License

Proprietary - All rights reserved

## Support

For issues or questions, please contact the development team.
