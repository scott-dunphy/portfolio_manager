import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box, Button, Typography, Paper, TextField, Grid, MenuItem
} from '@mui/material'
import { ArrowBack as ArrowBackIcon } from '@mui/icons-material'
import { propertyAPI, portfolioAPI } from '../services/api'

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
    valuation_method: 'growth'
  })

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

  const fetchProperty = async () => {
    try {
      const response = await propertyAPI.getById(id)
      setFormData(response.data)
    } catch (error) {
      console.error('Error fetching property:', error)
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
        await propertyAPI.update(id, formData)
      } else {
        await propertyAPI.create(formData)
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
                type="number"
                value={formData.purchase_price}
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
                type="number"
                value={formData.initial_noi}
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
