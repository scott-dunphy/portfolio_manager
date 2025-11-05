import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box, Typography, Paper, Grid, Tabs, Tab, Button,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow
} from '@mui/material'
import { ArrowBack as ArrowBackIcon } from '@mui/icons-material'
import { portfolioAPI, propertyAPI, loanAPI, preferredEquityAPI } from '../services/api'

function PortfolioDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [portfolio, setPortfolio] = useState(null)
  const [properties, setProperties] = useState([])
  const [loans, setLoans] = useState([])
  const [preferredEquities, setPreferredEquities] = useState([])
  const [tab, setTab] = useState(0)

  useEffect(() => {
    fetchPortfolioData()
  }, [id])

  const fetchPortfolioData = async () => {
    try {
      const [portfolioRes, propertiesRes, loansRes, prefEquityRes] = await Promise.all([
        portfolioAPI.getById(id),
        propertyAPI.getAll(id),
        loanAPI.getAll(id),
        preferredEquityAPI.getAll(id)
      ])
      setPortfolio(portfolioRes.data)
      setProperties(propertiesRes.data)
      setLoans(loansRes.data)
      setPreferredEquities(prefEquityRes.data)
    } catch (error) {
      console.error('Error fetching portfolio data:', error)
    }
  }

  if (!portfolio) return <Typography>Loading...</Typography>

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/')}>
          Back
        </Button>
        <Typography variant="h4" sx={{ ml: 2 }}>
          {portfolio.name}
        </Typography>
      </Box>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Grid container spacing={2}>
          <Grid item xs={6} sm={3}>
            <Typography variant="subtitle2" color="text.secondary">Start Date</Typography>
            <Typography>{portfolio.analysis_start_date}</Typography>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Typography variant="subtitle2" color="text.secondary">End Date</Typography>
            <Typography>{portfolio.analysis_end_date}</Typography>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Typography variant="subtitle2" color="text.secondary">Beginning Cash</Typography>
            <Typography>${portfolio.beginning_cash?.toLocaleString()}</Typography>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Typography variant="subtitle2" color="text.secondary">Beginning NAV</Typography>
            <Typography>${portfolio.beginning_nav?.toLocaleString()}</Typography>
          </Grid>
        </Grid>
      </Paper>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={tab} onChange={(e, v) => setTab(v)}>
          <Tab label={`Properties (${properties.length})`} />
          <Tab label={`Loans (${loans.length})`} />
          <Tab label={`Preferred Equity (${preferredEquities.length})`} />
        </Tabs>

        {tab === 0 && (
          <Box sx={{ p: 2 }}>
            <Button variant="contained" onClick={() => navigate('/properties/new')} sx={{ mb: 2 }}>
              Add Property
            </Button>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Property Name</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>City</TableCell>
                    <TableCell>State</TableCell>
                    <TableCell>Purchase Price</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {properties.map((property) => (
                    <TableRow key={property.id}>
                      <TableCell>{property.property_name}</TableCell>
                      <TableCell>{property.property_type}</TableCell>
                      <TableCell>{property.city}</TableCell>
                      <TableCell>{property.state}</TableCell>
                      <TableCell>${property.purchase_price?.toLocaleString()}</TableCell>
                      <TableCell>
                        <Button size="small" onClick={() => navigate(`/properties/${property.id}/edit`)}>
                          Edit
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}

        {tab === 1 && (
          <Box sx={{ p: 2 }}>
            <Button variant="contained" onClick={() => navigate('/loans/new')} sx={{ mb: 2 }}>
              Add Loan
            </Button>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Loan Name</TableCell>
                    <TableCell>Principal Amount</TableCell>
                    <TableCell>Interest Rate</TableCell>
                    <TableCell>Origination Date</TableCell>
                    <TableCell>Maturity Date</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {loans.map((loan) => (
                    <TableRow key={loan.id}>
                      <TableCell>{loan.loan_name}</TableCell>
                      <TableCell>${loan.principal_amount?.toLocaleString()}</TableCell>
                      <TableCell>{(loan.interest_rate * 100).toFixed(2)}%</TableCell>
                      <TableCell>{loan.origination_date}</TableCell>
                      <TableCell>{loan.maturity_date}</TableCell>
                      <TableCell>
                        <Button size="small" onClick={() => navigate(`/loans/${loan.id}/edit`)}>
                          Edit
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}

        {tab === 2 && (
          <Box sx={{ p: 2 }}>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Initial Investment</TableCell>
                    <TableCell>Preferred Return</TableCell>
                    <TableCell>Investment Date</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {preferredEquities.map((pe) => (
                    <TableRow key={pe.id}>
                      <TableCell>{pe.name}</TableCell>
                      <TableCell>${pe.initial_investment?.toLocaleString()}</TableCell>
                      <TableCell>{(pe.preferred_return * 100).toFixed(2)}%</TableCell>
                      <TableCell>{pe.investment_date}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}
      </Paper>
    </Box>
  )
}

export default PortfolioDetail
