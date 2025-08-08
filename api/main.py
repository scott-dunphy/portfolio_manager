from fastapi import FastAPI, UploadFile, File, HTTPException
from typing import Dict, Optional
from datetime import date
import tempfile
import os

from portfolio_manager.Portfolio import Portfolio
from portfolio_manager.Property import Property
from portfolio_manager.Loan import Loan

app = FastAPI(title="Portfolio Manager API")

# In-memory store for portfolio objects
PORTFOLIOS: Dict[str, Portfolio] = {}

def serialize_property(prop: Property) -> dict:
    """Convert a Property object into a JSON-serializable dict."""
    return {
        "id": prop.id,
        "name": prop.name,
        "property_type": prop.property_type,
        "acquisition_date": prop.acquisition_date.isoformat() if prop.acquisition_date else None,
        "disposition_date": prop.disposition_date.isoformat() if prop.disposition_date else None,
        "acquisition_cost": prop.acquisition_cost,
        "disposition_price": prop.disposition_price,
        "building_size": prop.building_size,
        "market_value": prop.market_value,
        "loans": list(prop.loans.keys()),
    }

def serialize_loan(loan: Loan) -> dict:
    """Convert a Loan object into a JSON-serializable dict."""
    return {
        "id": loan.id,
        "property_id": loan.property_id,
        "loan_amount": loan.loan_amount,
        "rate": loan.rate,
        "fund_date": loan.fund_date.isoformat() if loan.fund_date else None,
        "maturity_date": loan.maturity_date.isoformat() if loan.maturity_date else None,
        "payment_type": loan.payment_type,
    }

def get_portfolio_obj(portfolio_id: str) -> Portfolio:
    portfolio = PORTFOLIOS.get(portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio

@app.post("/upload")
async def upload_excel(portfolio_id: str, analysis_start_date: date, analysis_end_date: date, file: UploadFile = File(...)):
    """Upload an Excel file and create a Portfolio object."""
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload an .xlsx file.")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    try:
        contents = await file.read()
        tmp.write(contents)
        tmp.close()
        portfolio = Portfolio(analysis_start_date=analysis_start_date, analysis_end_date=analysis_end_date)
        portfolio.set_file_path(tmp.name)
        try:
            portfolio.load_data()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to load portfolio: {e}")
        PORTFOLIOS[portfolio_id] = portfolio
        return {"message": "Portfolio uploaded successfully", "portfolio_id": portfolio_id}
    finally:
        if os.path.exists(tmp.name):
            os.remove(tmp.name)

@app.get("/portfolios")
def list_portfolios():
    """Return a list of available portfolio IDs."""
    return list(PORTFOLIOS.keys())

@app.get("/portfolios/{portfolio_id}")
def get_portfolio(portfolio_id: str):
    portfolio = get_portfolio_obj(portfolio_id)
    loans = [loan.id for prop in portfolio.properties.values() for loan in prop.loans.values()]
    return {
        "id": portfolio_id,
        "properties": list(portfolio.properties.keys()),
        "loans": loans,
    }

@app.get("/portfolios/{portfolio_id}/properties")
def list_properties(portfolio_id: str):
    portfolio = get_portfolio_obj(portfolio_id)
    return [serialize_property(p) for p in portfolio.properties.values()]

@app.get("/portfolios/{portfolio_id}/properties/{property_id}")
def get_property(portfolio_id: str, property_id: str):
    portfolio = get_portfolio_obj(portfolio_id)
    prop = portfolio.properties.get(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return serialize_property(prop)

from pydantic import BaseModel

class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    market_value: Optional[float] = None
    building_size: Optional[float] = None

@app.put("/portfolios/{portfolio_id}/properties/{property_id}")
def update_property(portfolio_id: str, property_id: str, update: PropertyUpdate):
    portfolio = get_portfolio_obj(portfolio_id)
    prop = portfolio.properties.get(property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    for field, value in update.dict(exclude_unset=True).items():
        setattr(prop, field, value)
    return serialize_property(prop)

class LoanUpdate(BaseModel):
    loan_amount: Optional[float] = None
    rate: Optional[float] = None

@app.get("/portfolios/{portfolio_id}/loans")
def list_loans(portfolio_id: str):
    portfolio = get_portfolio_obj(portfolio_id)
    loans = []
    for prop in portfolio.properties.values():
        for loan in prop.loans.values():
            loans.append(serialize_loan(loan))
    return loans

@app.put("/portfolios/{portfolio_id}/loans/{loan_id}")
def update_loan(portfolio_id: str, loan_id: str, update: LoanUpdate):
    portfolio = get_portfolio_obj(portfolio_id)
    target_loan = None
    for prop in portfolio.properties.values():
        if loan_id in prop.loans:
            target_loan = prop.loans[loan_id]
            break
    if not target_loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    for field, value in update.dict(exclude_unset=True).items():
        setattr(target_loan, field, value)
    return serialize_loan(target_loan)
