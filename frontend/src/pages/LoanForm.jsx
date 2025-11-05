import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box, Button, Typography, Paper, TextField, Grid, MenuItem
} from '@mui/material'
import { ArrowBack as ArrowBackIcon } from '@mui/icons-material'
import { loanAPI, portfolioAPI, propertyAPI } from '../services/api'

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
    origination_date: '',
    maturity_date: '',
    payment_frequency: 'monthly',
    loan_type: '',
    amortization_period_months: '',
    io_period_months: 0,
    origination_fee: 0,
    exit_fee: 0
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

  const fetchLoan = async () => {
    try {
      const response = await loanAPI.getById(id)
      setFormData(response.data)
    } catch (error) {
      console.error('Error fetching loan:', error)
    }
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      if (id) {
        await loanAPI.update(id, formData)
      } else {
        await loanAPI.create(formData)
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
                {properties.map((property) => (
                  <MenuItem key={property.id} value={property.id}>
                    {property.property_name}
                  </MenuItem>
                ))}
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
                type="number"
                value={formData.principal_amount}
                onChange={handleChange}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Interest Rate (decimal, e.g., 0.05 for 5%)"
                name="interest_rate"
                type="number"
                value={formData.interest_rate}
                onChange={handleChange}
                inputProps={{ step: 0.001 }}
                required
              />
            </Grid>
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
                type="number"
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
                label="Origination Fee"
                name="origination_fee"
                type="number"
                value={formData.origination_fee}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Exit Fee"
                name="exit_fee"
                type="number"
                value={formData.exit_fee}
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
