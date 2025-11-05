import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box, Button, Card, CardContent, CardActions, Typography, Grid,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField,
  IconButton, Alert, Chip
} from '@mui/material'
import { Add as AddIcon, Delete as DeleteIcon, Edit as EditIcon, CheckCircle as CheckCircleIcon, Error as ErrorIcon } from '@mui/icons-material'
import { portfolioAPI } from '../services/api'
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
    valuation_method: 'growth'
  })

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
        valuation_method: portfolio.valuation_method
      })
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
        valuation_method: 'growth'
      })
    }
    setOpenDialog(true)
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
        await portfolioAPI.update(editingPortfolio.id, formData)
        fetchPortfolios()
        handleCloseDialog()
      } else {
        console.log('Creating new portfolio...')
        console.log('API endpoint: POST http://localhost:5000/api/portfolios')
        const response = await portfolioAPI.create(formData)
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

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Box>
          <Typography variant="h4">Portfolios</Typography>
          <Box sx={{ mt: 1 }}>
            {backendStatus === 'checking' && (
              <Chip label="Checking backend..." size="small" />
            )}
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
          </Box>
        </Box>
        <Box>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
            sx={{ mr: 1 }}
            disabled={backendStatus === 'disconnected'}
          >
            New Portfolio
          </Button>
          <Button
            variant="outlined"
            onClick={() => navigate('/upload')}
            disabled={backendStatus === 'disconnected'}
          >
            Upload Excel
          </Button>
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      <Grid container spacing={3}>
        {portfolios.map((portfolio) => (
          <Grid item xs={12} sm={6} md={4} key={portfolio.id}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {portfolio.name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Start: {portfolio.analysis_start_date}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  End: {portfolio.analysis_end_date}
                </Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Properties: {portfolio.property_count}
                </Typography>
                <Typography variant="body2">
                  Loans: {portfolio.loan_count}
                </Typography>
              </CardContent>
              <CardActions>
                <Button size="small" onClick={() => navigate(`/portfolios/${portfolio.id}`)}>
                  View Details
                </Button>
                <IconButton size="small" onClick={() => handleOpenDialog(portfolio)}>
                  <EditIcon fontSize="small" />
                </IconButton>
                <IconButton size="small" onClick={() => handleDelete(portfolio.id)} color="error">
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{editingPortfolio ? 'Edit Portfolio' : 'New Portfolio'}</DialogTitle>
        <DialogContent>
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
        </DialogContent>
        <DialogActions>
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
