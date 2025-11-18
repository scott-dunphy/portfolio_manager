import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Card,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Button
} from '@mui/material'
import { ArrowBack as ArrowBackIcon, Download as DownloadIcon } from '@mui/icons-material'
import { propertyTypeExposureAPI } from '../services/api'
import Plot from 'react-plotly.js'

function PropertyTypeExposure() {
  const { portfolioId } = useParams()
  const navigate = useNavigate()
  const [exposureData, setExposureData] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    fetchExposureData()
  }, [portfolioId])

  const fetchExposureData = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await propertyTypeExposureAPI.getExposure(portfolioId)
      const { transactions, ...exposureDataOnly } = response.data
      setExposureData(exposureDataOnly)
      setTransactions(transactions || [])
    } catch (err) {
      console.error('Error fetching exposure data:', err)
      setError('Failed to load property type exposure data')
    } finally {
      setLoading(false)
    }
  }

  const getChartData = () => {
    if (!exposureData || !exposureData.data || exposureData.data.length === 0) {
      return []
    }

    const data = exposureData.data
    const dates = data.map(d => d.date)
    const propertyTypes = exposureData.property_types

    // Helper to format currency
    const formatCurrency = (value) => {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      }).format(value)
    }

    // Create a trace for each property type as stacked 100% bars
    return propertyTypes.map((type) => {
      // Extract percentages and market values from data
      const percentages = data.map(d => {
        const typeData = d[type]
        return typeData?.percentage || 0
      })

      const marketValues = data.map(d => {
        const typeData = d[type]
        return typeData?.market_value || 0
      })

      // Create custom hover text
      const hoverText = dates.map((date, idx) => {
        const percentage = percentages[idx]
        const marketValue = marketValues[idx]
        return `<b>${type}</b><br>Date: ${date}<br>Exposure: ${percentage.toFixed(1)}%<br>Market Value: ${formatCurrency(marketValue)}`
      })

      return {
        x: dates,
        y: percentages,
        customdata: hoverText,
        name: type,
        type: 'bar',
        marker: {
          color: getColorForPropertyType(type, propertyTypes.indexOf(type))
        },
        hovertemplate: '%{customdata}<extra></extra>'
      }
    })
  }

  const getChartLayout = () => {
    return {
      title: {
        text: '<b>Property Type Exposure Over Time</b><br><sub>Quarterly Percentage Allocation (Sum to 100%)</sub>',
        x: 0.5,
        xanchor: 'center',
        font: { size: 16 }
      },
      xaxis: {
        title: 'Quarter End Date',
        showgrid: true,
        gridcolor: 'rgba(0, 0, 0, 0.1)',
        type: 'date'
      },
      yaxis: {
        title: 'Exposure (%)',
        showgrid: true,
        gridcolor: 'rgba(0, 0, 0, 0.1)',
        tickformat: '.0f',
        ticksuffix: '%',
        range: [0, 100]
      },
      barmode: 'stack',
      hovermode: 'x unified',
      plot_bgcolor: 'rgba(245, 247, 251, 0.5)',
      paper_bgcolor: 'white',
      font: {
        family: '"Inter", "Roboto", "Helvetica Neue", "Arial", sans-serif',
        size: 12
      },
      margin: { t: 100, r: 100, b: 80, l: 80 },
      height: 500,
      showlegend: true,
      legend: {
        orientation: 'v',
        yanchor: 'top',
        y: 0.99,
        xanchor: 'right',
        x: 0.99,
        bgcolor: 'rgba(255, 255, 255, 0.8)',
        bordercolor: 'rgba(0, 0, 0, 0.1)',
        borderwidth: 1
      }
    }
  }

  const getChartConfig = () => {
    return {
      responsive: true,
      displayModeBar: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['lasso2d', 'select2d']
    }
  }

  const getColorForPropertyType = (type, index) => {
    const colors = [
      '#4f46e5', // indigo
      '#f97316', // orange
      '#10b981', // emerald
      '#f43f5e', // rose
      '#3b82f6', // blue
      '#8b5cf6', // violet
      '#ec4899', // pink
      '#06b6d4', // cyan
      '#eab308', // lime
      '#6366f1', // indigo
      '#14b8a6', // teal
      '#f59e0b'  // amber
    ]
    return colors[index % colors.length]
  }

  const handleGoBack = () => {
    navigate(`/portfolios/${portfolioId}`)
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value)
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
  }

  const handleDownloadExcel = async () => {
    setDownloading(true)
    try {
      const response = await propertyTypeExposureAPI.downloadExcel(portfolioId)
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `Property_Type_Exposure.xlsx`)
      document.body.appendChild(link)
      link.click()
      link.parentChild.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Error downloading file:', err)
      setError('Failed to download exposure data')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography
            sx={{
              cursor: 'pointer',
              color: '#4f46e5',
              fontSize: 24,
              '&:hover': { opacity: 0.8 }
            }}
            onClick={handleGoBack}
          >
            <ArrowBackIcon sx={{ verticalAlign: 'middle', mr: 1 }} />
          </Typography>
          <Typography variant="h4">Property Type Exposure Analysis</Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={handleDownloadExcel}
          disabled={downloading}
        >
          {downloading ? 'Downloading...' : 'Download'}
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : exposureData && exposureData.data && exposureData.data.length > 0 ? (
        <>
          <Card sx={{ mb: 3 }}>
            <Box sx={{ p: 3 }}>
              <Plot
                data={getChartData()}
                layout={getChartLayout()}
                config={getChartConfig()}
                style={{ width: '100%' }}
              />
            </Box>
          </Card>

          {transactions && transactions.length > 0 && (
            <Card>
              <Box sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ mb: 2 }}>
                  Acquisitions & Dispositions
                </Typography>
                <TableContainer component={Paper}>
                  <Table>
                    <TableHead>
                      <TableRow sx={{ backgroundColor: '#eef2ff' }}>
                        <TableCell>Transaction Date</TableCell>
                        <TableCell>Property Name</TableCell>
                        <TableCell>Property Type</TableCell>
                        <TableCell>Transaction Type</TableCell>
                        <TableCell align="right">Transaction Price</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {transactions.map((transaction, idx) => (
                        <TableRow key={idx}>
                          <TableCell>{formatDate(transaction.transaction_date)}</TableCell>
                          <TableCell>{transaction.property_name}</TableCell>
                          <TableCell>{transaction.property_type}</TableCell>
                          <TableCell>
                            <Chip
                              label={transaction.transaction_type === 'acquisition' ? 'Acquisition' : 'Disposition'}
                              color={transaction.transaction_type === 'acquisition' ? 'success' : 'error'}
                              variant="outlined"
                              size="small"
                            />
                          </TableCell>
                          <TableCell align="right">
                            {formatCurrency(transaction.transaction_price)}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            </Card>
          )}
        </>
      ) : (
        <Card>
          <Box sx={{ p: 3 }}>
            <Alert severity="info">
              No property type exposure data available. Please ensure properties have market value and valuation data configured.
            </Alert>
          </Box>
        </Card>
      )}
    </Box>
  )
}

export default PropertyTypeExposure
