import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert,
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  IconButton,
  Paper,
  Stack,
  TextField,
  Typography,
  FormControlLabel,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow
} from '@mui/material'
import { Add as AddIcon, Delete as DeleteIcon, Edit as EditIcon, CheckCircle as CheckCircleIcon, Error as ErrorIcon } from '@mui/icons-material'
import { portfolioAPI, propertyAPI } from '../services/api'
import api from '../services/api'

function PortfolioList() {
  const navigate = useNavigate()
  const [portfolios, setPortfolios] = useState([])
  const [openDialog, setOpenDialog] = useState(false)
  const [editingPortfolio, setEditingPortfolio] = useState(null)
  const [error, setError] = useState('')
  const [dialogError, setDialogError] = useState('')
  const [loading, setLoading] = useState(false)
  const [backendStatus, setBackendStatus] = useState('checking') // 'checking', 'connected', 'disconnected'
const [formData, setFormData] = useState({
  name: '',
  analysis_start_date: '',
  analysis_end_date: '',
  initial_unfunded_equity: 0,
  beginning_cash: 0,
  fee: 0,
  beginning_nav: 0,
  valuation_method: 'growth',
  auto_refinance_enabled: false
})
const [propertyTypes, setPropertyTypes] = useState([])
const [refiSpreads, setRefiSpreads] = useState({})

  useEffect(() => {
    checkBackendHealth()
    fetchPortfolios()
  }, [])

  const checkBackendHealth = async () => {
    try {
      await api.get('/health')
      setBackendStatus('connected')
      console.log('Backend health check: OK')
    } catch (error) {
      setBackendStatus('disconnected')
      console.error('Backend health check failed:', error)
      setError('Backend server is not responding. Please start the backend server on port 5000.')
    }
  }

  const fetchPortfolios = async () => {
    try {
      const response = await portfolioAPI.getAll()
      setPortfolios(response.data)
    } catch (error) {
      setError('Failed to load portfolios')
      console.error('Error fetching portfolios:', error)
    }
  }

  const handleOpenDialog = (portfolio = null) => {
    if (portfolio) {
      setEditingPortfolio(portfolio)
      setFormData({
        name: portfolio.name,
        analysis_start_date: portfolio.analysis_start_date,
        analysis_end_date: portfolio.analysis_end_date,
        initial_unfunded_equity: portfolio.initial_unfunded_equity,
        beginning_cash: portfolio.beginning_cash,
        fee: portfolio.fee,
        beginning_nav: portfolio.beginning_nav,
        valuation_method: portfolio.valuation_method,
        auto_refinance_enabled: Boolean(portfolio.auto_refinance_enabled)
      })
      const spreads = portfolio.auto_refinance_spreads || {}
      setRefiSpreads(Object.entries(spreads).reduce((acc, [key, value]) => {
        acc[key] = value != null ? String(value) : ''
        return acc
      }, {}))
      loadPropertyTypes(portfolio.id)
    } else {
      setEditingPortfolio(null)
      setFormData({
        name: '',
        analysis_start_date: '',
        analysis_end_date: '',
        initial_unfunded_equity: 0,
        beginning_cash: 0,
        fee: 0,
        beginning_nav: 0,
        valuation_method: 'growth',
        auto_refinance_enabled: false
      })
      setRefiSpreads({})
      setPropertyTypes([])
    }
    setOpenDialog(true)
  }

  const loadPropertyTypes = async (portfolioId) => {
    if (!portfolioId) {
      setPropertyTypes([])
      return
    }
    try {
      const response = await propertyAPI.getTypes(portfolioId)
      setPropertyTypes(response.data || [])
    } catch (err) {
      console.error('Error loading property types', err)
      setPropertyTypes([])
    }
  }

  const handleCloseDialog = () => {
    setOpenDialog(false)
    setEditingPortfolio(null)
    setDialogError('')
  }

  const handleSubmit = async () => {
    // Clear previous errors
    setDialogError('')

    // Validate required fields
    if (!formData.name || !formData.name.trim()) {
      setDialogError('Portfolio name is required')
      return
    }
    if (!formData.analysis_start_date) {
      setDialogError('Start date is required')
      return
    }
    if (!formData.analysis_end_date) {
      setDialogError('End date is required')
      return
    }

    // Validate date order
    if (new Date(formData.analysis_start_date) > new Date(formData.analysis_end_date)) {
      setDialogError('Start date must be before end date')
      return
    }

    setLoading(true)
    console.log('Submitting portfolio with data:', formData)
    try {
      if (editingPortfolio) {
        console.log('Updating portfolio:', editingPortfolio.id)
        await portfolioAPI.update(editingPortfolio.id, {
          ...formData,
          auto_refinance_spreads: buildSpreadPayload()
        })
        fetchPortfolios()
        handleCloseDialog()
      } else {
        console.log('Creating new portfolio...')
        console.log('API endpoint: POST http://localhost:5000/api/portfolios')
        const response = await portfolioAPI.create({
          ...formData,
          auto_refinance_spreads: buildSpreadPayload()
        })
        console.log('Portfolio created successfully:', response.data)
        handleCloseDialog()
        // Navigate to setup page for new portfolios
        navigate(`/portfolios/${response.data.id}/setup`)
      }
    } catch (error) {
      console.error('Full error object:', error)
      console.error('Error response:', error.response)
      console.error('Error message:', error.message)
      console.error('Error code:', error.code)

      let errorMessage = 'Failed to save portfolio'

      if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
        errorMessage = 'Cannot connect to backend server. Please ensure the backend is running on http://localhost:5000'
      } else if (error.response?.data?.error) {
        errorMessage = error.response.data.error
      } else if (error.message) {
        errorMessage = error.message
      }

      setDialogError(errorMessage)
      console.error('Error saving portfolio:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this portfolio?')) {
      try {
        await portfolioAPI.delete(id)
        fetchPortfolios()
      } catch (error) {
        setError('Failed to delete portfolio')
        console.error('Error deleting portfolio:', error)
      }
    }
  }

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const propertyTypeOptions = React.useMemo(() => {
    const unique = new Set(['default', 'Unassigned', ...propertyTypes])
    return Array.from(unique)
  }, [propertyTypes])

  const handleSpreadChange = (type, value) => {
    setRefiSpreads((prev) => ({
      ...prev,
      [type]: value
    }))
  }

  const buildSpreadPayload = () => {
    const payload = {}
    propertyTypeOptions.forEach((type) => {
      const raw = refiSpreads[type]
      if (raw != null && String(raw).trim() !== '') {
        const numeric = Number(raw)
        if (!Number.isNaN(numeric)) {
          payload[type] = numeric
        }
      }
    })
    return payload
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Paper
        variant="outlined"
        sx={{
          p: { xs: 3, md: 5 },
          borderRadius: 4,
          border: '1px solid rgba(79, 70, 229, 0.18)',
          background: 'linear-gradient(135deg, rgba(79,70,229,0.1) 0%, rgba(14,165,233,0.1) 100%)'
        }}
      >
        <Box
          sx={{
            display: 'flex',
            flexDirection: { xs: 'column', md: 'row' },
            alignItems: { xs: 'flex-start', md: 'center' },
            justifyContent: 'space-between',
            gap: 3
          }}
        >
          <Box>
            <Typography variant="overline" sx={{ color: 'primary.main', fontWeight: 700 }}>
              Portfolio workspace
            </Typography>
            <Typography variant="h4" sx={{ mt: 1 }}>
              Manage portfolios, properties, and loans in one view
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
              Build cash-flow ready portfolios, import Excel models, and monitor exposure with modern Material styling.
            </Typography>
            <Stack
              direction="row"
              spacing={1}
              useFlexGap
              sx={{ mt: 3, flexWrap: 'wrap' }}
            >
              {backendStatus === 'checking' && <Chip label="Checking backend..." size="small" />}
              {backendStatus === 'connected' && (
                <Chip
                  icon={<CheckCircleIcon />}
                  label="Backend Connected"
                  color="success"
                  size="small"
                />
              )}
              {backendStatus === 'disconnected' && (
                <Chip
                  icon={<ErrorIcon />}
                  label="Backend Disconnected"
                  color="error"
                  size="small"
                  onClick={checkBackendHealth}
                />
              )}
            </Stack>
          </Box>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} width={{ xs: '100%', md: 'auto' }}>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              fullWidth
              onClick={() => handleOpenDialog()}
              disabled={backendStatus === 'disconnected'}
            >
              New Portfolio
            </Button>
            <Button
              variant="outlined"
              fullWidth
              onClick={() => navigate('/upload')}
              disabled={backendStatus === 'disconnected'}
            >
              Upload Excel
            </Button>
          </Stack>
        </Box>
      </Paper>

      {error && (
        <Alert severity="error" onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {portfolios.map((portfolio) => (
          <Grid item xs={12} sm={6} md={4} key={portfolio.id}>
            <Card
              variant="outlined"
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                background: 'linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(245,247,251,0.95) 100%)'
              }}
            >
              <CardContent sx={{ flexGrow: 1 }}>
                <Typography variant="subtitle2" color="primary.main" sx={{ fontWeight: 600, letterSpacing: 0.8 }}>
                  Portfolio
                </Typography>
                <Typography variant="h6" gutterBottom sx={{ mt: 0.5 }}>
                  {portfolio.name}
                </Typography>
                <Stack spacing={0.5} sx={{ mt: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Analysis Window
                  </Typography>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    {portfolio.analysis_start_date} - {portfolio.analysis_end_date}
                  </Typography>
                </Stack>
                <Stack direction="row" spacing={3} sx={{ mt: 3 }}>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Properties
                    </Typography>
                    <Typography variant="h5">{portfolio.property_count}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Loans
                    </Typography>
                    <Typography variant="h5">{portfolio.loan_count}</Typography>
                  </Box>
                </Stack>
              </CardContent>
              <CardActions sx={{ justifyContent: 'space-between', alignItems: 'center', px: 3, pb: 3 }}>
                <Button size="small" onClick={() => navigate(`/portfolios/${portfolio.id}`)}>
                  View Details
                </Button>
                <Box>
                  <IconButton size="small" onClick={() => handleOpenDialog(portfolio)}>
                    <EditIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={() => handleDelete(portfolio.id)} color="error">
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Box>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Dialog
        open={openDialog}
        onClose={handleCloseDialog}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 4,
            p: 1.5
          }
        }}
      >
        <DialogTitle sx={{ fontWeight: 600 }}>
          {editingPortfolio ? 'Edit Portfolio' : 'New Portfolio'}
        </DialogTitle>
        <DialogContent dividers sx={{ pt: 2 }}>
          {dialogError && <Alert severity="error" sx={{ mb: 2 }}>{dialogError}</Alert>}
          <TextField
            fullWidth
            margin="normal"
            label="Portfolio Name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            required
            disabled={loading}
          />
          <TextField
            fullWidth
            margin="normal"
            label="Start Date"
            name="analysis_start_date"
            type="date"
            value={formData.analysis_start_date}
            onChange={handleChange}
            InputLabelProps={{ shrink: true }}
            required
            disabled={loading}
          />
          <TextField
            fullWidth
            margin="normal"
            label="End Date"
            name="analysis_end_date"
            type="date"
            value={formData.analysis_end_date}
            onChange={handleChange}
            InputLabelProps={{ shrink: true }}
            required
            disabled={loading}
          />
          <TextField
            fullWidth
            margin="normal"
            label="Initial Unfunded Equity"
            name="initial_unfunded_equity"
            type="number"
            value={formData.initial_unfunded_equity}
            onChange={handleChange}
            disabled={loading}
          />
          <TextField
            fullWidth
            margin="normal"
            label="Beginning Cash"
            name="beginning_cash"
            type="number"
            value={formData.beginning_cash}
            onChange={handleChange}
            disabled={loading}
          />
          <TextField
            fullWidth
            margin="normal"
            label="Fee"
            name="fee"
            type="number"
            value={formData.fee}
            onChange={handleChange}
            disabled={loading}
          />
          <TextField
            fullWidth
            margin="normal"
            label="Beginning NAV"
            name="beginning_nav"
            type="number"
            value={formData.beginning_nav}
            onChange={handleChange}
            disabled={loading}
          />
          <FormControlLabel
            sx={{ mt: 2 }}
            control={
              <Switch
                checked={formData.auto_refinance_enabled}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    auto_refinance_enabled: e.target.checked
                  }))
                }
                disabled={loading}
              />
            }
            label="Automatically refinance loans at maturity"
          />
          {formData.auto_refinance_enabled && (
            <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, mt: 2, p: 2 }}>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Refinance Spreads (decimal)
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Property Type</TableCell>
                    <TableCell align="right">Spread</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {propertyTypeOptions.map((type) => (
                    <TableRow key={type}>
                      <TableCell>{type === 'default' ? 'Default (fallback)' : type}</TableCell>
                      <TableCell align="right">
                        <TextField
                          size="small"
                          type="number"
                          inputProps={{ step: 0.0001 }}
                          value={refiSpreads[type] ?? ''}
                          onChange={(e) => handleSpreadChange(type, e.target.value)}
                          disabled={loading}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                  {propertyTypeOptions.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={2}>
                        <Typography variant="body2" color="text.secondary">
                          Add properties to configure spreads.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={handleCloseDialog} disabled={loading}>Cancel</Button>
          <Button onClick={handleSubmit} variant="contained" disabled={loading}>
            {loading ? 'Saving...' : editingPortfolio ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default PortfolioList
