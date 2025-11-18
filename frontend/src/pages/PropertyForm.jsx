import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box, Button, Typography, Paper, TextField, Grid, MenuItem, Divider, FormControlLabel, Checkbox
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
    market_value_start: '',
    purchase_date: '',
    exit_date: '',
    exit_cap_rate: '',
    year_1_cap_rate: '',
    calculated_year1_cap_rate: '',
    building_size: '',
    noi_growth_rate: '',
    initial_noi: '',
    valuation_method: 'growth',
    ownership_percent: 1,
    capex_percent_of_noi: '',
    disposition_price_override: '',
    encumbrance_override: false,
    encumbrance_note: '',
    has_active_loan: false,
    is_encumbered: false,
    encumbrance_periods: []
  })
  const [encumbranceNoteError, setEncumbranceNoteError] = useState('')
  const [focusedCurrencyField, setFocusedCurrencyField] = useState(null)
  const [associatedLoans, setAssociatedLoans] = useState([])
  const manualEncumbranceDisabled = formData.has_active_loan
  const computedEncumbrance = formData.has_active_loan || formData.encumbrance_override

  const handleEncumbranceOverrideChange = (checked) => {
    if (manualEncumbranceDisabled) {
      return
    }
    setFormData(prev => ({
      ...prev,
      encumbrance_override: checked
    }))
    if (!checked) {
      setEncumbranceNoteError('')
    }
  }

  const handleEncumbranceNoteChange = (value) => {
    setFormData(prev => ({
      ...prev,
      encumbrance_note: value
    }))
    if (value.trim()) {
      setEncumbranceNoteError('')
    }
  }

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

  const currencyFields = new Set([
    'purchase_price',
    'initial_noi',
    'market_value_start',
    'disposition_price_override'
  ])

  const getCurrencyValue = (name) => {
    const raw = formData[name] ?? ''
    if (focusedCurrencyField === name) {
      return raw
    }
    return formatCurrencyInputValue(raw)
  }

  const formatLoanCurrency = (value) => {
    if (value === null || value === undefined || value === '') {
      return '—'
    }
    const asNumber = Number(value)
    if (Number.isNaN(asNumber)) {
      return String(value)
    }
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0
    }).format(asNumber)
  }

  const formatLoanDate = (value) => {
    if (!value) {
      return '—'
    }
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) {
      return value
    }
    return date.toLocaleDateString()
  }


  const fetchProperty = async () => {
    try {
      const response = await propertyAPI.getById(id)
      const data = response.data
      setAssociatedLoans(Array.isArray(data.loans) ? data.loans : [])
      setFormData(prev => ({
        ...prev,
        ...data,
        purchase_price: data.purchase_price != null ? String(Math.round(data.purchase_price)) : '',
        market_value_start:
          data.market_value_start != null ? String(Math.round(data.market_value_start)) : '',
        initial_noi: data.initial_noi != null ? String(Math.round(data.initial_noi)) : '',
        capex_percent_of_noi:
          data.capex_percent_of_noi != null ? String(data.capex_percent_of_noi) : '',
        calculated_year1_cap_rate: data.calculated_year1_cap_rate ?? data.year_1_cap_rate ?? '',
        disposition_price_override:
          data.disposition_price_override != null
            ? String(Math.round(data.disposition_price_override))
            : '',
        encumbrance_override: Boolean(data.encumbrance_override),
        encumbrance_note: data.encumbrance_note || '',
        has_active_loan: Boolean(data.has_active_loan),
        is_encumbered: Boolean(data.is_encumbered),
        encumbrance_periods: Array.isArray(data.encumbrance_periods) ? data.encumbrance_periods : []
      }))
      setEncumbranceNoteError('')
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
    if (formData.encumbrance_override && !formData.encumbrance_note.trim()) {
      setEncumbranceNoteError('Please explain why the property is encumbered.')
      return
    }
    setEncumbranceNoteError('')
    try {
      const {
        calculated_year1_cap_rate,
        has_active_loan,
        is_encumbered,
        ...rest
      } = formData
      const payload = {
        ...rest,
        purchase_price: formData.purchase_price ? Number(formData.purchase_price) : null,
        market_value_start: formData.market_value_start ? Number(formData.market_value_start) : null,
        initial_noi: formData.initial_noi ? Number(formData.initial_noi) : null,
        capex_percent_of_noi:
          formData.capex_percent_of_noi === '' ? null : Number(formData.capex_percent_of_noi),
        disposition_price_override:
          formData.disposition_price_override === '' ? null : Number(formData.disposition_price_override),
        encumbrance_override: Boolean(formData.encumbrance_override),
        encumbrance_note: formData.encumbrance_override ? formData.encumbrance_note.trim() : null
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
                label="Market Value (Analysis Start)"
                name="market_value_start"
                type="text"
                inputMode="numeric"
                value={getCurrencyValue('market_value_start')}
                onFocus={() => setFocusedCurrencyField('market_value_start')}
                onBlur={() => setFocusedCurrencyField(null)}
                onChange={handleChange}
                required
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
                label="Year 1 Cap Rate (Calculated)"
                name="year_1_cap_rate"
                type="number"
                value={
                  formData.calculated_year1_cap_rate !== ''
                    ? formData.calculated_year1_cap_rate
                    : formData.year_1_cap_rate
                }
                InputProps={{ readOnly: true }}
                helperText="Automatically calculated after saving"
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
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Disposition Price Override"
                name="disposition_price_override"
                type="text"
                inputMode="numeric"
                value={getCurrencyValue('disposition_price_override')}
                onFocus={() => setFocusedCurrencyField('disposition_price_override')}
                onBlur={() => setFocusedCurrencyField(null)}
                onChange={handleChange}
                helperText="Leave blank to use NOI/exit cap calculation"
              />
            </Grid>
            <Grid item xs={12}>
              <Box
                sx={{
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  p: 2
                }}
              >
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Encumbrance
                </Typography>
                <FormControlLabel
                  control={<Checkbox checked={computedEncumbrance} disabled />}
                  label={
                    formData.has_active_loan
                      ? 'Encumbered (active loan)'
                      : formData.encumbrance_override
                      ? 'Encumbered (manual override)'
                      : 'Unencumbered'
                  }
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={formData.encumbrance_override}
                      onChange={(e) => handleEncumbranceOverrideChange(e.target.checked)}
                      disabled={manualEncumbranceDisabled}
                    />
                  }
                  label="Manually mark as encumbered"
                />
                {formData.has_active_loan && (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: formData.encumbrance_override ? 1 : 0 }}>
                    Active debt automatically marks this property as encumbered.
                  </Typography>
                )}
                {formData.encumbrance_override && (
                  <TextField
                    fullWidth
                    label="Encumbrance Note"
                    value={formData.encumbrance_note}
                    onChange={(e) => handleEncumbranceNoteChange(e.target.value)}
                    required
                    error={Boolean(encumbranceNoteError)}
                    helperText={
                      encumbranceNoteError || 'Explain why the property is encumbered without debt'
                    }
                    sx={{ mt: 1 }}
                  />
                )}
              </Box>
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
      {id && (
        <Paper sx={{ p: 3, mt: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6">Linked Loans</Typography>
            <Button size="small" onClick={() => navigate('/loans/new')} variant="text">
              Add Loan
            </Button>
          </Box>
          {associatedLoans.length === 0 ? (
            <Typography color="text.secondary">No loans are currently linked to this property.</Typography>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {associatedLoans.map((loan, index) => (
                <Box
                  key={loan.id || `${loan.loan_id}-${index}`}
                  sx={{
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 2,
                    p: 2
                  }}
                >
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Box>
                      <Typography variant="subtitle1">
                        {loan.loan_name || loan.loan_id || `Loan #${loan.id}`}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        ID: {loan.loan_id || loan.id} • Type: {loan.loan_type || 'N/A'}
                      </Typography>
                    </Box>
                    {loan.id && (
                      <Button size="small" variant="outlined" onClick={() => navigate(`/loans/${loan.id}/edit`)}>
                        Open Loan
                      </Button>
                    )}
                  </Box>
                  <Divider sx={{ my: 1.5 }} />
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6} md={4}>
                      <Typography variant="body2" color="text.secondary">
                        Principal Amount
                      </Typography>
                      <Typography sx={{ fontWeight: 600 }}>{formatLoanCurrency(loan.principal_amount)}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={6} md={4}>
                      <Typography variant="body2" color="text.secondary">
                        Interest Rate
                      </Typography>
                      <Typography sx={{ fontWeight: 600 }}>
                        {loan.interest_rate != null ? `${(Number(loan.interest_rate) * 100).toFixed(2)}%` : '—'}
                      </Typography>
                    </Grid>
                    <Grid item xs={12} sm={6} md={4}>
                      <Typography variant="body2" color="text.secondary">
                        Maturity Date
                      </Typography>
                      <Typography sx={{ fontWeight: 600 }}>{formatLoanDate(loan.maturity_date)}</Typography>
                    </Grid>
                  </Grid>
                </Box>
              ))}
            </Box>
          )}
        </Paper>
      )}
    </Box>
  )
}

export default PropertyForm
