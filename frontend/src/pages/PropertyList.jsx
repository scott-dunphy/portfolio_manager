import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box, Button, Typography, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Paper, IconButton
} from '@mui/material'
import { Add as AddIcon, Edit as EditIcon, Delete as DeleteIcon } from '@mui/icons-material'
import { propertyAPI } from '../services/api'
import { formatCurrencyDisplay } from '../utils/numberFormat'

function PropertyList() {
  const navigate = useNavigate()
  const [properties, setProperties] = useState([])

  useEffect(() => {
    fetchProperties()
  }, [])

  const fetchProperties = async () => {
    try {
      const response = await propertyAPI.getAll()
      setProperties(response.data)
    } catch (error) {
      console.error('Error fetching properties:', error)
    }
  }

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this property?')) {
      try {
        await propertyAPI.delete(id)
        fetchProperties()
      } catch (error) {
        console.error('Error deleting property:', error)
      }
    }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Properties</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/properties/new')}
        >
          New Property
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Property ID</TableCell>
              <TableCell>Name</TableCell>
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
                <TableCell>{property.property_id}</TableCell>
                <TableCell>{property.property_name}</TableCell>
                <TableCell>{property.property_type}</TableCell>
                <TableCell>{property.city}</TableCell>
                <TableCell>{property.state}</TableCell>
                <TableCell>{formatCurrency(property.purchase_price)}</TableCell>
                <TableCell>
                  <IconButton size="small" onClick={() => navigate(`/properties/${property.id}/edit`)}>
                    <EditIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={() => handleDelete(property.id)} color="error">
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

export default PropertyList
  const formatCurrency = (value) => {
    const formatted = formatCurrencyDisplay(value)
    if (formatted === '—') {
      return formatted
    }
    return `$${formatted}`
  }
