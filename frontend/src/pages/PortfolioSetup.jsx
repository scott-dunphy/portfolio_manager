import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box, Button, Typography, Paper, TextField, Grid, Card, CardContent,
  CardActions, IconButton, Accordion, AccordionSummary, AccordionDetails,
  Divider, Alert, MenuItem, Chip, Switch, FormControlLabel, Table,
  TableBody, TableCell, TableHead, TableRow
} from '@mui/material'
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
  Check as CheckIcon
} from '@mui/icons-material'
import { portfolioAPI, propertyAPI, loanAPI } from '../services/api'
import { formatCurrencyDisplay, formatCurrencyInputValue, sanitizeCurrencyInput } from '../utils/numberFormat'

function PortfolioSetup() {
  const { portfolioId } = useParams()
  const navigate = useNavigate()
  const [portfolio, setPortfolio] = useState(null)
  const [properties, setProperties] = useState([])
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [propertyTypes, setPropertyTypes] = useState([])
  const [autoRefiEnabled, setAutoRefiEnabled] = useState(false)
  const [refiSpreads, setRefiSpreads] = useState({})
  const [savingRefi, setSavingRefi] = useState(false)

  // Property form state
  const [showPropertyForm, setShowPropertyForm] = useState(false)
  const [propertyFormData, setPropertyFormData] = useState({
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
    capex_percent_of_noi: ''
  })

  // Loan form state
  const [selectedPropertyForLoan, setSelectedPropertyForLoan] = useState(null)
  const [showLoanForm, setShowLoanForm] = useState(false)
  const [loanFormData, setLoanFormData] = useState({
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
    fetchPortfolio()
    fetchProperties()
  }, [portfolioId])

  useEffect(() => {
    if (portfolio) {
      setAutoRefiEnabled(Boolean(portfolio.auto_refinance_enabled))
      const spreads = portfolio.auto_refinance_spreads || {}
      const mapped = Object.entries(spreads).reduce((acc, [key, value]) => {
        acc[key] = value !== undefined && value !== null ? String(value) : ''
        return acc
      }, {})
      setRefiSpreads(mapped)
    }
  }, [portfolio])

  useEffect(() => {
    if (showLoanForm && properties.length > 0 && !selectedPropertyForLoan) {
      setSelectedPropertyForLoan(properties[0])
    }
  }, [showLoanForm, properties, selectedPropertyForLoan])

  const fetchPortfolio = async () => {
    try {
      const response = await portfolioAPI.getById(portfolioId)
      setPortfolio(response.data)
    } catch (error) {
      setError('Failed to load portfolio')
      console.error('Error fetching portfolio:', error)
    }
  }

  const fetchProperties = async () => {
    try {
      const response = await propertyAPI.getAll(portfolioId)
      // Fetch loans for each property
      const propertiesWithLoans = await Promise.all(
        response.data.map(async (property) => {
          try {
            const loansResponse = await loanAPI.getAll(portfolioId)
            const propertyLoans = loansResponse.data.filter(
              loan => loan.property_id === property.id
            )
            return { ...property, loans: propertyLoans }
          } catch (err) {
            console.error('Error fetching loans for property:', err)
            return { ...property, loans: [] }
          }
        })
      )
      setProperties(propertiesWithLoans)
      loadPropertyTypes()
    } catch (error) {
      console.error('Error fetching properties:', error)
      setProperties([])
    }
  }

  const loadPropertyTypes = async () => {
    try {
      const response = await propertyAPI.getTypes(portfolioId)
      setPropertyTypes(response.data || [])
    } catch (error) {
      console.error('Error fetching property types:', error)
    }
  }

  const resetPropertyForm = () => {
    setPropertyFormData({
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
      capex_percent_of_noi: ''
    })
  }

  const resetLoanForm = () => {
    setLoanFormData({
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
  }

  const currencyFields = new Set(['purchase_price', 'initial_noi', 'market_value_start'])
  const [focusedPropertyCurrencyField, setFocusedPropertyCurrencyField] = useState(null)

  const formatCurrency = (value) => {
    const formatted = formatCurrencyDisplay(value)
    if (formatted === '—') {
      return formatted
    }
    return `$${formatted}`
  }

  const formatLoanRate = (loan) => {
    if (loan.rate_type === 'floating') {
      const spread = loan.sofr_spread != null ? (loan.sofr_spread * 100).toFixed(2) : '0.00'
      return `SOFR + ${spread}%`
    }
    if (loan.interest_rate != null) {
      return `${(parseFloat(loan.interest_rate) * 100).toFixed(2)}%`
    }
    return '—'
  }

  const getPropertyCurrencyValue = (name) => {
    const raw = propertyFormData[name] ?? ''
    if (focusedPropertyCurrencyField === name) {
      return raw
    }
    return formatCurrencyInputValue(raw)
  }

  const handlePropertyChange = (e) => {
    const { name, value } = e.target
    setPropertyFormData(prev => ({
      ...prev,
      [name]: currencyFields.has(name) ? sanitizeCurrencyInput(value) : value
    }))
  }

  const handleLoanChange = (e) => {
    const { name, value } = e.target
    setLoanFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleLoanPropertySelect = (value) => {
    const propertyId = Number(value)
    if (Number.isNaN(propertyId)) {
      setSelectedPropertyForLoan(null)
      return
    }
    const property = properties.find(p => p.id === propertyId) || null
    setSelectedPropertyForLoan(property)
  }

  const handleAddProperty = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    try {
      const { calculated_year1_cap_rate, ...rest } = propertyFormData
      await propertyAPI.create({
        ...rest,
        portfolio_id: portfolioId,
        purchase_price: propertyFormData.purchase_price ? Number(propertyFormData.purchase_price) : null,
        market_value_start: propertyFormData.market_value_start ? Number(propertyFormData.market_value_start) : null,
        initial_noi: propertyFormData.initial_noi ? Number(propertyFormData.initial_noi) : null,
        capex_percent_of_noi:
          propertyFormData.capex_percent_of_noi === '' ? null : Number(propertyFormData.capex_percent_of_noi)
      })
      setSuccess('Property added successfully!')
      resetPropertyForm()
      setShowPropertyForm(false)
      fetchProperties()
    } catch (error) {
      setError('Failed to add property: ' + (error.response?.data?.error || error.message))
      console.error('Error adding property:', error)
    }
  }

  const handleAddLoan = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (!selectedPropertyForLoan) {
      setError('Please select a property for this loan')
      return
    }

    try {
      await loanAPI.create({
        ...loanFormData,
        portfolio_id: portfolioId,
        property_id: selectedPropertyForLoan.id
      })
      setSuccess('Loan added successfully!')
      resetLoanForm()
      setShowLoanForm(false)
      setSelectedPropertyForLoan(null)
      fetchProperties()
    } catch (error) {
      setError('Failed to add loan: ' + (error.response?.data?.error || error.message))
      console.error('Error adding loan:', error)
    }
  }

  const handleDeleteProperty = async (propertyId) => {
    if (window.confirm('Are you sure you want to delete this property and all its loans?')) {
      try {
        await propertyAPI.delete(propertyId)
        setSuccess('Property deleted successfully!')
        fetchProperties()
      } catch (error) {
        setError('Failed to delete property')
        console.error('Error deleting property:', error)
      }
    }
  }

  const handleDeleteLoan = async (loanId) => {
    if (window.confirm('Are you sure you want to delete this loan?')) {
      try {
        await loanAPI.delete(loanId)
        setSuccess('Loan deleted successfully!')
        fetchProperties()
      } catch (error) {
        setError('Failed to delete loan')
        console.error('Error deleting loan:', error)
      }
    }
  }

  const handleAddLoanToProperty = (property) => {
    setSelectedPropertyForLoan(property)
    setShowLoanForm(true)
    setShowPropertyForm(false)
  }

  const handleFinish = () => {
    navigate('/portfolios/' + portfolioId)
  }

  const propertyTypeOptions = React.useMemo(() => {
    const unique = new Set(['default', ...propertyTypes])
    return Array.from(unique)
  }, [propertyTypes])

  const handleSpreadChange = (type, value) => {
    setRefiSpreads((prev) => ({
      ...prev,
      [type]: value
    }))
  }

  const handleSaveRefiSettings = async () => {
    setSavingRefi(true)
    setError('')
    try {
      const payloadSpreads = {}
      propertyTypeOptions.forEach((type) => {
        const rawValue = refiSpreads[type]
        if (rawValue !== undefined && rawValue !== null && String(rawValue).trim() !== '') {
          const numeric = Number(rawValue)
          if (!Number.isNaN(numeric)) {
            payloadSpreads[type] = numeric
          }
        }
      })
      await portfolioAPI.update(portfolioId, {
        auto_refinance_enabled: autoRefiEnabled,
        auto_refinance_spreads: payloadSpreads
      })
      setSuccess('Refinance settings saved.')
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to save refinance settings.')
    } finally {
      setSavingRefi(false)
    }
  }

  if (!portfolio) {
    return <Typography>Loading...</Typography>
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4">Set Up Portfolio: {portfolio.name}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Add properties and loans to your portfolio
          </Typography>
        </Box>
        <Button variant="outlined" onClick={handleFinish}>
          Done
        </Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>{success}</Alert>}

      <Grid container spacing={3}>
        {/* Left side - Forms */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Add Property</Typography>
              {!showPropertyForm && (
                <Button
                  variant="contained"
                  startIcon={<AddIcon />}
                  onClick={() => {
                    setShowPropertyForm(true)
                    setShowLoanForm(false)
                    setSelectedPropertyForLoan(null)
                  }}
                  size="small"
                >
                  New Property
                </Button>
              )}
            </Box>

            {showPropertyForm && (
              <form onSubmit={handleAddProperty}>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Property ID"
                      name="property_id"
                      value={propertyFormData.property_id}
                      onChange={handlePropertyChange}
                      required
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Property Name"
                      name="property_name"
                      value={propertyFormData.property_name}
                      onChange={handlePropertyChange}
                      required
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Property Type"
                      name="property_type"
                      value={propertyFormData.property_type}
                      onChange={handlePropertyChange}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Ownership %"
                      name="ownership_percent"
                      type="number"
                      value={propertyFormData.ownership_percent}
                      onChange={handlePropertyChange}
                      size="small"
                      inputProps={{ step: 0.01, min: 0, max: 1 }}
                      helperText="Enter as decimal (e.g., 1 = 100%)"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Purchase Price"
                      name="purchase_price"
                      type="text"
                      inputMode="numeric"
                      value={getPropertyCurrencyValue('purchase_price')}
                      onFocus={() => setFocusedPropertyCurrencyField('purchase_price')}
                      onBlur={() => setFocusedPropertyCurrencyField(null)}
                      onChange={handlePropertyChange}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Market Value (Analysis Start)"
                      name="market_value_start"
                      type="text"
                      inputMode="numeric"
                      value={getPropertyCurrencyValue('market_value_start')}
                      onFocus={() => setFocusedPropertyCurrencyField('market_value_start')}
                      onBlur={() => setFocusedPropertyCurrencyField(null)}
                      onChange={handlePropertyChange}
                      size="small"
                      required
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Address"
                      name="address"
                      value={propertyFormData.address}
                      onChange={handlePropertyChange}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <TextField
                      fullWidth
                      label="City"
                      name="city"
                      value={propertyFormData.city}
                      onChange={handlePropertyChange}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <TextField
                      fullWidth
                      label="State"
                      name="state"
                      value={propertyFormData.state}
                      onChange={handlePropertyChange}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <TextField
                      fullWidth
                      label="Zip Code"
                      name="zip_code"
                      value={propertyFormData.zip_code}
                      onChange={handlePropertyChange}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Purchase Date"
                      name="purchase_date"
                      type="date"
                      value={propertyFormData.purchase_date}
                      onChange={handlePropertyChange}
                      InputLabelProps={{ shrink: true }}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Building Size (sq ft)"
                      name="building_size"
                      type="number"
                      value={propertyFormData.building_size}
                      onChange={handlePropertyChange}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Initial NOI"
                      name="initial_noi"
                      type="text"
                      inputMode="numeric"
                      value={getPropertyCurrencyValue('initial_noi')}
                      onFocus={() => setFocusedPropertyCurrencyField('initial_noi')}
                      onBlur={() => setFocusedPropertyCurrencyField(null)}
                      onChange={handlePropertyChange}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Exit Date"
                      name="exit_date"
                      type="date"
                      value={propertyFormData.exit_date}
                      onChange={handlePropertyChange}
                      InputLabelProps={{ shrink: true }}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="NOI Growth Rate"
                      name="noi_growth_rate"
                      type="number"
                      value={propertyFormData.noi_growth_rate}
                      onChange={handlePropertyChange}
                      inputProps={{ step: 0.01 }}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Year 1 Cap Rate (Calculated)"
                      name="year_1_cap_rate"
                      type="number"
                      value={
                        propertyFormData.calculated_year1_cap_rate !== ''
                          ? propertyFormData.calculated_year1_cap_rate
                          : propertyFormData.year_1_cap_rate
                      }
                      InputProps={{ readOnly: true }}
                      helperText="Auto-calculated after property is saved"
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Exit Cap Rate"
                      name="exit_cap_rate"
                      type="number"
                      value={propertyFormData.exit_cap_rate}
                      onChange={handlePropertyChange}
                      inputProps={{ step: 0.01 }}
                      required
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Capex % of NOI"
                      name="capex_percent_of_noi"
                      type="number"
                      value={propertyFormData.capex_percent_of_noi}
                      onChange={handlePropertyChange}
                      inputProps={{ step: 0.01, min: 0 }}
                      helperText="Enter decimal (e.g., 0.1 = 10%)"
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="Valuation Method"
                      name="valuation_method"
                      value={propertyFormData.valuation_method}
                      onChange={handlePropertyChange}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                      <Button
                        onClick={() => {
                          setShowPropertyForm(false)
                          resetPropertyForm()
                        }}
                      >
                        Cancel
                      </Button>
                      <Button type="submit" variant="contained">
                        Add Property
                      </Button>
                    </Box>
                  </Grid>
                </Grid>
              </form>
            )}
          </Paper>

          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>Auto Refinance Settings</Typography>
            <FormControlLabel
              control={
                <Switch
                  checked={autoRefiEnabled}
                  onChange={(e) => setAutoRefiEnabled(e.target.checked)}
                />
              }
              label="Automatically refinance loans at maturity"
            />
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Refinance loans into 10-year, interest-only debt using the Chatham 10-year forward Treasury curve plus the spreads below.
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Property Type</TableCell>
                  <TableCell align="right">Spread (decimal)</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {propertyTypeOptions.map((type) => (
                  <TableRow key={type}>
                    <TableCell>
                      {type === 'default' ? 'Default (fallback)' : type}
                    </TableCell>
                    <TableCell align="right">
                      <TextField
                        size="small"
                        type="number"
                        inputProps={{ step: 0.0001 }}
                        value={refiSpreads[type] ?? ''}
                        onChange={(e) => handleSpreadChange(type, e.target.value)}
                        disabled={!autoRefiEnabled}
                      />
                    </TableCell>
                  </TableRow>
                ))}
                {propertyTypeOptions.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={2}>
                      <Typography variant="body2" color="text.secondary">
                        Add a property to configure spreads.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
              <Button
                variant="contained"
                onClick={handleSaveRefiSettings}
                disabled={savingRefi}
              >
                {savingRefi ? 'Saving...' : 'Save Settings'}
              </Button>
            </Box>
          </Paper>

          <Paper sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Add Loan</Typography>
              {!showLoanForm && properties.length > 0 && (
                <Button
                  variant="contained"
                  startIcon={<AddIcon />}
                  onClick={() => {
                    if (properties.length === 0) {
                      setError('Please add a property first')
                      return
                    }
                    setShowLoanForm(true)
                    setShowPropertyForm(false)
                    setSelectedPropertyForLoan(properties[0] || null)
                  }}
                  size="small"
                >
                  New Loan
                </Button>
              )}
            </Box>

            {properties.length === 0 && !showLoanForm && (
              <Typography variant="body2" color="text.secondary">
                Add a property first to create loans
              </Typography>
            )}

            {showLoanForm && (
              <form onSubmit={handleAddLoan}>
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      select
                      label="Property"
                      value={selectedPropertyForLoan ? String(selectedPropertyForLoan.id) : ''}
                      onChange={(e) => handleLoanPropertySelect(e.target.value)}
                      required
                      size="small"
                    >
                      {properties.map((property) => {
                        const label = property.property_name
                          ? `${property.property_name} (${property.property_id})`
                          : property.property_id
                        return (
                          <MenuItem key={property.id} value={String(property.id)}>
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
                      value={loanFormData.loan_id}
                      onChange={handleLoanChange}
                      required
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Loan Name"
                      name="loan_name"
                      value={loanFormData.loan_name}
                      onChange={handleLoanChange}
                      required
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Principal Amount"
                      name="principal_amount"
                      type="number"
                      value={loanFormData.principal_amount}
                      onChange={handleLoanChange}
                      required
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Interest Rate (decimal)"
                      name="interest_rate"
                      type="number"
                      value={loanFormData.interest_rate}
                      onChange={handleLoanChange}
                      inputProps={{ step: 0.001 }}
                      required
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Origination Date"
                      name="origination_date"
                      type="date"
                      value={loanFormData.origination_date}
                      onChange={handleLoanChange}
                      InputLabelProps={{ shrink: true }}
                      required
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Maturity Date"
                      name="maturity_date"
                      type="date"
                      value={loanFormData.maturity_date}
                      onChange={handleLoanChange}
                      InputLabelProps={{ shrink: true }}
                      required
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      select
                      label="Payment Frequency"
                      name="payment_frequency"
                      value={loanFormData.payment_frequency}
                      onChange={handleLoanChange}
                      size="small"
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
                      value={loanFormData.loan_type}
                      onChange={handleLoanChange}
                      size="small"
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                      <Button
                        onClick={() => {
                          setShowLoanForm(false)
                          setSelectedPropertyForLoan(null)
                          resetLoanForm()
                        }}
                      >
                        Cancel
                      </Button>
                      <Button type="submit" variant="contained">
                        Add Loan
                      </Button>
                    </Box>
                  </Grid>
                </Grid>
              </form>
            )}
          </Paper>
        </Grid>

        {/* Right side - Property and Loan List */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Properties & Loans ({properties.length} {properties.length === 1 ? 'property' : 'properties'})
            </Typography>

            {properties.length === 0 ? (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <Typography variant="body2" color="text.secondary">
                  No properties added yet. Add your first property to get started.
                </Typography>
              </Box>
            ) : (
              <Box>
                {properties.map((property, index) => (
                  <Accordion key={property.id} defaultExpanded={index === 0}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', pr: 2 }}>
                        <Box>
                          <Typography variant="subtitle1">{property.property_name}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {property.property_id} • {property.loans?.length || 0} loan{property.loans?.length === 1 ? '' : 's'}
                          </Typography>
                        </Box>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Box>
                        <Grid container spacing={1} sx={{ mb: 2 }}>
                          {property.address && (
                            <Grid item xs={12}>
                              <Typography variant="body2">
                                <strong>Address:</strong> {property.address}
                                {property.city && `, ${property.city}`}
                                {property.state && `, ${property.state}`}
                                {property.zip_code && ` ${property.zip_code}`}
                              </Typography>
                            </Grid>
                          )}
                          {property.property_type && (
                            <Grid item xs={12} sm={6}>
                              <Typography variant="body2">
                                <strong>Type:</strong> {property.property_type}
                              </Typography>
                            </Grid>
                          )}
                          {property.purchase_price && (
                            <Grid item xs={12} sm={6}>
                              <Typography variant="body2">
                                <strong>Purchase Price:</strong> {formatCurrency(property.purchase_price)}
                              </Typography>
                            </Grid>
                          )}
                          {property.capex_percent_of_noi != null && (
                            <Grid item xs={12} sm={6}>
                              <Typography variant="body2">
                                <strong>Capex % of NOI:</strong> {(Number(property.capex_percent_of_noi) * 100).toFixed(2)}%
                              </Typography>
                            </Grid>
                          )}
                        </Grid>

                        <Divider sx={{ my: 2 }} />

                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                          <Typography variant="subtitle2">Loans</Typography>
                          <Button
                            size="small"
                            startIcon={<AddIcon />}
                            onClick={() => handleAddLoanToProperty(property)}
                          >
                            Add Loan
                          </Button>
                        </Box>

                        {property.loans && property.loans.length > 0 ? (
                          <Box sx={{ pl: 2 }}>
                            {property.loans.map((loan) => (
                              <Card key={loan.id} variant="outlined" sx={{ mb: 1 }}>
                                <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                    <Box>
                                      <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                                        {loan.loan_name}
                                      </Typography>
                                      <Typography variant="caption" color="text.secondary">
                                        {loan.loan_id}
                                      </Typography>
                                      <Typography variant="body2" sx={{ mt: 0.5 }}>
                                        Principal: {formatCurrency(loan.principal_amount)}
                                      </Typography>
                                      <Typography variant="body2">
                                        Rate: {formatLoanRate(loan)}
                                      </Typography>
                                    </Box>
                                    <IconButton
                                      size="small"
                                      color="error"
                                      onClick={() => handleDeleteLoan(loan.id)}
                                    >
                                      <DeleteIcon fontSize="small" />
                                    </IconButton>
                                  </Box>
                                </CardContent>
                              </Card>
                            ))}
                          </Box>
                        ) : (
                          <Typography variant="body2" color="text.secondary" sx={{ pl: 2, fontStyle: 'italic' }}>
                            No loans added yet
                          </Typography>
                        )}

                        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
                          <Button
                            size="small"
                            color="error"
                            startIcon={<DeleteIcon />}
                            onClick={() => handleDeleteProperty(property.id)}
                          >
                            Delete Property
                          </Button>
                        </Box>
                      </Box>
                    </AccordionDetails>
                  </Accordion>
                ))}
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>

      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'center' }}>
        <Button
          variant="contained"
          size="large"
          startIcon={<CheckIcon />}
          onClick={handleFinish}
        >
          Finish Setup
        </Button>
      </Box>
    </Box>
  )
}

export default PortfolioSetup
