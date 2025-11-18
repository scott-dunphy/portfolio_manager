import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box, Button, Typography, Paper, TextField, Grid, MenuItem
} from '@mui/material'
import { ArrowBack as ArrowBackIcon } from '@mui/icons-material'
import { loanAPI, portfolioAPI, propertyAPI } from '../services/api'
import {
  formatCurrencyInputValue,
  sanitizeCurrencyInput
} from '../utils/numberFormat'

function LoanForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [portfolios, setPortfolios] = useState([])
  const [properties, setProperties] = useState([])
  const [formData, setFormData] = useState({
    portfolio_id: '',
    property_id: '',
    loan_id: '',
    loan_name: '',
    principal_amount: '',
    interest_rate: '',
    rate_type: 'fixed',
    sofr_spread: '',
    origination_date: '',
    maturity_date: '',
    payment_frequency: 'monthly',
    loan_type: '',
    amortization_period_months: '',
    io_period_months: 0,
    origination_fee: '',
    exit_fee: '',
    interest_day_count: '30/360'
  })

  useEffect(() => {
    fetchPortfolios()
    if (id) {
      fetchLoan()
    }
  }, [id])

  useEffect(() => {
    if (formData.portfolio_id) {
      fetchProperties(formData.portfolio_id)
    }
  }, [formData.portfolio_id])

  const fetchPortfolios = async () => {
    try {
      const response = await portfolioAPI.getAll()
      setPortfolios(response.data)
    } catch (error) {
      console.error('Error fetching portfolios:', error)
    }
  }

  const fetchProperties = async (portfolioId) => {
    try {
      const response = await propertyAPI.getAll(portfolioId)
      setProperties(response.data)
    } catch (error) {
      console.error('Error fetching properties:', error)
    }
  }

  const currencyFields = new Set(['principal_amount', 'exit_fee'])
  const [focusedCurrencyField, setFocusedCurrencyField] = useState(null)

  const getCurrencyFieldValue = (name) => {
    const raw = formData[name] ?? ''
    if (focusedCurrencyField === name) {
      return raw
    }
    return formatCurrencyInputValue(raw)
  }

  const handleCurrencyFocus = (name) => setFocusedCurrencyField(name)
  const handleCurrencyBlur = () => setFocusedCurrencyField(null)

  const fetchLoan = async () => {
    try {
      const response = await loanAPI.getById(id)
      const data = response.data
      setFormData(prev => ({
        ...prev,
        ...data,
        rate_type: data.rate_type || 'fixed',
        interest_day_count: data.interest_day_count || '30/360',
        principal_amount: data.principal_amount != null ? String(Math.round(data.principal_amount)) : '',
        origination_fee: data.origination_fee != null ? String(data.origination_fee) : '',
        exit_fee: data.exit_fee != null ? String(Math.round(data.exit_fee)) : '',
        sofr_spread: data.sofr_spread != null ? String(data.sofr_spread) : ''
      }))
    } catch (error) {
      console.error('Error fetching loan:', error)
    }
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    if (currencyFields.has(name)) {
      setFormData(prev => ({ ...prev, [name]: sanitizeCurrencyInput(value) }))
    } else {
      setFormData(prev => ({ ...prev, [name]: value }))
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const payload = {
        ...formData,
        principal_amount: Number(formData.principal_amount || 0),
        origination_fee: formData.origination_fee === '' ? 0 : Number(formData.origination_fee),
        exit_fee: formData.exit_fee === '' ? 0 : Number(formData.exit_fee),
        sofr_spread: formData.sofr_spread === '' ? 0 : Number(formData.sofr_spread),
        interest_day_count: formData.interest_day_count,
        interest_rate:
          formData.rate_type === 'fixed'
            ? Number(formData.interest_rate || 0)
            : Number(formData.interest_rate || 0)
      }
      if (id) {
        await loanAPI.update(id, payload)
      } else {
        await loanAPI.create(payload)
      }
      navigate(-1)
    } catch (error) {
      console.error('Error saving loan:', error)
    }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate(-1)}>
          Back
        </Button>
        <Typography variant="h4" sx={{ ml: 2 }}>
          {id ? 'Edit Loan' : 'New Loan'}
        </Typography>
      </Box>

      <Paper sx={{ p: 3 }}>
        <form onSubmit={handleSubmit}>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="Portfolio"
                name="portfolio_id"
                value={formData.portfolio_id}
                onChange={handleChange}
                required
              >
                {portfolios.map((portfolio) => (
                  <MenuItem key={portfolio.id} value={portfolio.id}>
                    {portfolio.name}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="Property (Optional)"
                name="property_id"
                value={formData.property_id}
                onChange={handleChange}
              >
                <MenuItem value="">None</MenuItem>
                {properties.map((property) => {
                  const label = property.property_name
                    ? `${property.property_name} (${property.property_id})`
                    : property.property_id
                  return (
                    <MenuItem key={property.id} value={property.id}>
                      {label}
                    </MenuItem>
                  )
                })}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Loan ID"
                name="loan_id"
                value={formData.loan_id}
                onChange={handleChange}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Loan Name"
                name="loan_name"
                value={formData.loan_name}
                onChange={handleChange}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Principal Amount"
                name="principal_amount"
                type="text"
                inputMode="numeric"
                value={getCurrencyFieldValue('principal_amount')}
                onFocus={() => handleCurrencyFocus('principal_amount')}
                onBlur={handleCurrencyBlur}
                onChange={handleChange}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Interest Rate (decimal, e.g., 0.05 for 5%)"
                name="interest_rate"
                type="text"
                inputMode="numeric"
                value={formData.interest_rate}
                onChange={handleChange}
                inputProps={{ step: 0.001 }}
                required={formData.rate_type === 'fixed'}
                disabled={formData.rate_type === 'floating'}
                helperText={formData.rate_type === 'floating' ? 'Floating loans use SOFR forward curve + spread' : ''}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="Rate Type"
                name="rate_type"
                value={formData.rate_type}
                onChange={handleChange}
              >
                <MenuItem value="fixed">Fixed</MenuItem>
                <MenuItem value="floating">Floating (SOFR + Spread)</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="Day Count Convention"
                name="interest_day_count"
                value={formData.interest_day_count}
                onChange={handleChange}
                helperText="Controls how interest accrues between payment dates"
              >
                <MenuItem value="30/360">30 / 360</MenuItem>
                <MenuItem value="actual/360">Actual / 360</MenuItem>
                <MenuItem value="actual/365">Actual / 365</MenuItem>
              </TextField>
            </Grid>
            {formData.rate_type === 'floating' && (
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Spread over SOFR (decimal, e.g., 0.02)"
                  name="sofr_spread"
                  type="text"
                  inputMode="numeric"
                  value={formData.sofr_spread}
                  onChange={handleChange}
                  helperText="Decimal format (0.02 = 200 bps)"
                />
              </Grid>
            )}
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Origination Date"
                name="origination_date"
                type="date"
                value={formData.origination_date}
                onChange={handleChange}
                InputLabelProps={{ shrink: true }}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Maturity Date"
                name="maturity_date"
                type="date"
                value={formData.maturity_date}
                onChange={handleChange}
                InputLabelProps={{ shrink: true }}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                select
                label="Payment Frequency"
                name="payment_frequency"
                value={formData.payment_frequency}
                onChange={handleChange}
              >
                <MenuItem value="monthly">Monthly</MenuItem>
                <MenuItem value="quarterly">Quarterly</MenuItem>
                <MenuItem value="annually">Annually</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Loan Type"
                name="loan_type"
                value={formData.loan_type}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Amortization Period (months)"
                name="amortization_period_months"
                type="text"
                inputMode="numeric"
                value={formData.amortization_period_months}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Interest-Only Period (months)"
                name="io_period_months"
                type="number"
                value={formData.io_period_months}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                type="number"
                inputProps={{ step: 0.0001, min: 0 }}
                label="Origination Fee (% of principal, decimal)"
                name="origination_fee"
                value={formData.origination_fee}
                onChange={handleChange}
                helperText="Enter as decimal (e.g. 0.01 for 1%)"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Exit Fee"
                name="exit_fee"
                type="text"
                inputMode="numeric"
                value={getCurrencyFieldValue('exit_fee')}
                onFocus={() => handleCurrencyFocus('exit_fee')}
                onBlur={handleCurrencyBlur}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                <Button onClick={() => navigate(-1)}>Cancel</Button>
                <Button type="submit" variant="contained">
                  {id ? 'Update' : 'Create'} Loan
                </Button>
              </Box>
            </Grid>
          </Grid>
        </form>
      </Paper>
    </Box>
  )
}

export default LoanForm
