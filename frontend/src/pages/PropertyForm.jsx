import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box, Button, Typography, Paper, TextField, Grid, MenuItem
} from '@mui/material'
import { ArrowBack as ArrowBackIcon } from '@mui/icons-material'
import { propertyAPI, portfolioAPI } from '../services/api'
import {
  formatCurrencyInputValue,
  sanitizeCurrencyInput
} from '../utils/numberFormat'

function PropertyForm() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [portfolios, setPortfolios] = useState([])
  const [formData, setFormData] = useState({
    portfolio_id: '',
    property_id: '',
    property_name: '',
    property_type: '',
    address: '',
    city: '',
    state: '',
    zip_code: '',
    purchase_price: '',
    purchase_date: '',
    exit_date: '',
    exit_cap_rate: '',
    year_1_cap_rate: '',
    building_size: '',
    noi_growth_rate: '',
    initial_noi: '',
    valuation_method: 'growth',
    ownership_percent: 1,
    capex_percent_of_noi: ''
  })
  const [focusedCurrencyField, setFocusedCurrencyField] = useState(null)

  useEffect(() => {
    fetchPortfolios()
    if (id) {
      fetchProperty()
    }
  }, [id])

  const fetchPortfolios = async () => {
    try {
      const response = await portfolioAPI.getAll()
      setPortfolios(response.data)
    } catch (error) {
      console.error('Error fetching portfolios:', error)
    }
  }

  const currencyFields = new Set(['purchase_price', 'initial_noi'])

  const getCurrencyValue = (name) => {
    const raw = formData[name] ?? ''
    if (focusedCurrencyField === name) {
      return raw
    }
    return formatCurrencyInputValue(raw)
  }


  const fetchProperty = async () => {
    try {
      const response = await propertyAPI.getById(id)
      const data = response.data
      setFormData(prev => ({
        ...prev,
        ...data,
        purchase_price: data.purchase_price != null ? String(Math.round(data.purchase_price)) : '',
        initial_noi: data.initial_noi != null ? String(Math.round(data.initial_noi)) : '',
        capex_percent_of_noi:
          data.capex_percent_of_noi != null ? String(data.capex_percent_of_noi) : ''
      }))
    } catch (error) {
      console.error('Error fetching property:', error)
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
        purchase_price: formData.purchase_price ? Number(formData.purchase_price) : null,
        initial_noi: formData.initial_noi ? Number(formData.initial_noi) : null,
        capex_percent_of_noi:
          formData.capex_percent_of_noi === '' ? null : Number(formData.capex_percent_of_noi)
      }
      if (id) {
        await propertyAPI.update(id, payload)
      } else {
        await propertyAPI.create(payload)
      }
      navigate(-1)
    } catch (error) {
      console.error('Error saving property:', error)
    }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate(-1)}>
          Back
        </Button>
        <Typography variant="h4" sx={{ ml: 2 }}>
          {id ? 'Edit Property' : 'New Property'}
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
                label="Property ID"
                name="property_id"
                value={formData.property_id}
                onChange={handleChange}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Property Name"
                name="property_name"
                value={formData.property_name}
                onChange={handleChange}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Property Type"
                name="property_type"
                value={formData.property_type}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Ownership %"
                name="ownership_percent"
                type="text"
                inputMode="numeric"
                value={formData.ownership_percent ?? ''}
                onChange={handleChange}
                inputProps={{ step: 0.01, min: 0, max: 1 }}
                helperText="Enter as decimal (e.g., 1 = 100%)"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Capex % of NOI"
                name="capex_percent_of_noi"
                type="number"
                value={formData.capex_percent_of_noi}
                onChange={handleChange}
                inputProps={{ step: 0.01, min: 0 }}
                helperText="Decimal percent of NOI (e.g., 0.1 = 10%)"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Address"
                name="address"
                value={formData.address}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="City"
                name="city"
                value={formData.city}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="State"
                name="state"
                value={formData.state}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Zip Code"
                name="zip_code"
                value={formData.zip_code}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Purchase Price"
                name="purchase_price"
                type="text"
                inputMode="numeric"
                value={getCurrencyValue('purchase_price')}
                onFocus={() => setFocusedCurrencyField('purchase_price')}
                onBlur={() => setFocusedCurrencyField(null)}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Building Size (sq ft)"
                name="building_size"
                type="number"
                value={formData.building_size}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Purchase Date"
                name="purchase_date"
                type="date"
                value={formData.purchase_date}
                onChange={handleChange}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Exit Date"
                name="exit_date"
                type="date"
                value={formData.exit_date}
                onChange={handleChange}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Initial NOI"
                name="initial_noi"
                type="text"
                inputMode="numeric"
                value={getCurrencyValue('initial_noi')}
                onFocus={() => setFocusedCurrencyField('initial_noi')}
                onBlur={() => setFocusedCurrencyField(null)}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="NOI Growth Rate"
                name="noi_growth_rate"
                type="number"
                value={formData.noi_growth_rate}
                onChange={handleChange}
                inputProps={{ step: 0.01 }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Year 1 Cap Rate"
                name="year_1_cap_rate"
                type="number"
                value={formData.year_1_cap_rate}
                onChange={handleChange}
                inputProps={{ step: 0.01 }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Exit Cap Rate"
                name="exit_cap_rate"
                type="number"
                value={formData.exit_cap_rate}
                onChange={handleChange}
                inputProps={{ step: 0.01 }}
              />
            </Grid>
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                <Button onClick={() => navigate(-1)}>Cancel</Button>
                <Button type="submit" variant="contained">
                  {id ? 'Update' : 'Create'} Property
                </Button>
              </Box>
            </Grid>
          </Grid>
        </form>
      </Paper>
    </Box>
  )
}

export default PropertyForm
