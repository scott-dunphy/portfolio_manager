import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box, Button, Typography, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Paper, IconButton
} from '@mui/material'
import { Add as AddIcon, Edit as EditIcon, Delete as DeleteIcon } from '@mui/icons-material'
import { loanAPI } from '../services/api'
import { formatCurrencyDisplay } from '../utils/numberFormat'

const formatCurrency = (value) => {
  const formatted = formatCurrencyDisplay(value)
  if (formatted === '—') {
    return formatted
  }
  return `$${formatted}`
}

const formatRateLabel = (loan) => {
  if (loan.rate_type === 'floating') {
    const spread = loan.sofr_spread != null ? (loan.sofr_spread * 100).toFixed(2) : '0.00'
    return `SOFR + ${spread}%`
  }
  return loan.interest_rate != null ? `${(loan.interest_rate * 100).toFixed(2)}%` : '—'
}

function LoanList() {
  const navigate = useNavigate()
  const [loans, setLoans] = useState([])

  useEffect(() => {
    fetchLoans()
  }, [])

  const fetchLoans = async () => {
    try {
      const response = await loanAPI.getAll()
      setLoans(response.data)
    } catch (error) {
      console.error('Error fetching loans:', error)
    }
  }

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this loan?')) {
      try {
        await loanAPI.delete(id)
        fetchLoans()
      } catch (error) {
        console.error('Error deleting loan:', error)
      }
    }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Loans</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/loans/new')}
        >
          New Loan
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Loan ID</TableCell>
              <TableCell>Loan Name</TableCell>
              <TableCell>Principal Amount</TableCell>
              <TableCell>Rate</TableCell>
              <TableCell>Origination Date</TableCell>
              <TableCell>Maturity Date</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loans.map((loan) => (
              <TableRow key={loan.id}>
                <TableCell>{loan.loan_id}</TableCell>
                <TableCell>{loan.loan_name}</TableCell>
                <TableCell>{formatCurrency(loan.principal_amount)}</TableCell>
                <TableCell>{formatRateLabel(loan)}</TableCell>
                <TableCell>{loan.origination_date}</TableCell>
                <TableCell>{loan.maturity_date}</TableCell>
                <TableCell>
                  <IconButton size="small" onClick={() => navigate(`/loans/${loan.id}/edit`)}>
                    <EditIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={() => handleDelete(loan.id)} color="error">
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}

export default LoanList
