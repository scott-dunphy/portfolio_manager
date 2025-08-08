from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict

app = FastAPI()

# In-memory stores
portfolios: Dict[int, Dict] = {}
properties: Dict[int, Dict] = {}
loans: Dict[int, Dict] = {}

class Portfolio(BaseModel):
    id: int
    name: str

class Property(BaseModel):
    id: int
    address: str
    value: float

class Loan(BaseModel):
    id: int
    amount: float
    rate: float

@app.post('/upload')
async def upload(file: UploadFile = File(...)):
    data = await file.read()
    return {"filename": file.filename, "size": len(data)}

# Portfolio endpoints
@app.get('/api/portfolios')
def list_portfolios():
    return list(portfolios.values())

@app.get('/api/portfolios/{item_id}')
def get_portfolio(item_id: int):
    item = portfolios.get(item_id)
    if not item:
        raise HTTPException(404)
    return item

@app.put('/api/portfolios/{item_id}')
def update_portfolio(item_id: int, payload: Portfolio):
    portfolios[item_id] = payload.dict()
    return portfolios[item_id]

# Property endpoints
@app.get('/api/properties')
def list_properties():
    return list(properties.values())

@app.get('/api/properties/{item_id}')
def get_property(item_id: int):
    item = properties.get(item_id)
    if not item:
        raise HTTPException(404)
    return item

@app.put('/api/properties/{item_id}')
def update_property(item_id: int, payload: Property):
    properties[item_id] = payload.dict()
    return properties[item_id]

# Loan endpoints
@app.get('/api/loans')
def list_loans():
    return list(loans.values())

@app.get('/api/loans/{item_id}')
def get_loan(item_id: int):
    item = loans.get(item_id)
    if not item:
        raise HTTPException(404)
    return item

@app.put('/api/loans/{item_id}')
def update_loan(item_id: int, payload: Loan):
    loans[item_id] = payload.dict()
    return loans[item_id]

# Serve frontend
app.mount('/', StaticFiles(directory='frontend/dist', html=True), name='frontend')
