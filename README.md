# Portfolio Manager API

This project exposes a simple web API for interacting with `Portfolio`, `Property`, and `Loan` objects.
The API is built with [FastAPI](https://fastapi.tiangolo.com/) and loads data from Excel spreadsheets
using the existing `Portfolio.read_import_file` and related loader methods.

## Running the server

Install dependencies and start the development server:

```bash
pip install fastapi uvicorn
uvicorn portfolio_manager.api.main:app --reload
```

## Endpoints

### `POST /upload`
Upload an Excel (`.xlsx`) spreadsheet and create a portfolio.

Query parameters:
- `portfolio_id` – identifier for the portfolio
- `analysis_start_date` – start date of the analysis (YYYY-MM-DD)
- `analysis_end_date` – end date of the analysis (YYYY-MM-DD)

Body: multipart form with the Excel file under the `file` field.

### `GET /portfolios`
Return a list of loaded portfolio identifiers.

### `GET /portfolios/{portfolio_id}`
Retrieve summary information about a specific portfolio.

### `GET /portfolios/{portfolio_id}/properties`
List all properties in a portfolio.

### `GET /portfolios/{portfolio_id}/properties/{property_id}`
Retrieve a single property.

### `PUT /portfolios/{portfolio_id}/properties/{property_id}`
Update fields on a property. Supply a JSON body with any of:
`name`, `market_value`, or `building_size`.

### `GET /portfolios/{portfolio_id}/loans`
List all loans across properties in a portfolio.

### `PUT /portfolios/{portfolio_id}/loans/{loan_id}`
Update a loan. Supply a JSON body with any of: `loan_amount`, `rate`.

## Error handling

- Uploads that are not `.xlsx` files return `400 Bad Request`.
- Malformed spreadsheets or loading errors also return `400 Bad Request`
  with details about the failure.

