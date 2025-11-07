import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import {
  Box, Button, Typography, Paper, MenuItem, TextField, Alert,
  CircularProgress, List, ListItem, ListItemText
} from '@mui/material'
import { CloudUpload as CloudUploadIcon, ArrowBack as ArrowBackIcon, Download as DownloadIcon } from '@mui/icons-material'
import { uploadAPI, portfolioAPI } from '../services/api'

function ExcelUpload() {
  const navigate = useNavigate()
  const [portfolios, setPortfolios] = useState([])
  const [selectedPortfolio, setSelectedPortfolio] = useState('')
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchPortfolios()
  }, [])

  const fetchPortfolios = async () => {
    try {
      const response = await portfolioAPI.getAll()
      setPortfolios(response.data)
    } catch (error) {
      console.error('Error fetching portfolios:', error)
    }
  }

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0])
      setError('')
      setResult(null)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls']
    },
    maxFiles: 1
  })

  const handleUpload = async () => {
    if (!file || !selectedPortfolio) {
      setError('Please select a portfolio and upload a file')
      return
    }

    setUploading(true)
    setError('')
    setResult(null)

    try {
      const response = await uploadAPI.uploadExcel(file, selectedPortfolio)
      setResult(response.data)
      setFile(null)
    } catch (error) {
      setError(error.response?.data?.error || 'Failed to upload file')
      console.error('Error uploading file:', error)
    } finally {
      setUploading(false)
    }
  }

  const handleDownloadTemplate = async () => {
    try {
      const response = await uploadAPI.downloadTemplate()
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'Property_Import_Template.xlsx')
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Error downloading template:', error)
      setError('Failed to download template')
    }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/')}>
          Back
        </Button>
        <Typography variant="h4" sx={{ ml: 2 }}>
          Upload Excel File
        </Typography>
      </Box>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ mb: 3 }}>
          <Button
            variant="outlined"
            startIcon={<DownloadIcon />}
            onClick={handleDownloadTemplate}
            sx={{ mb: 2 }}
          >
            Download Template
          </Button>
          <Typography variant="body2" color="text.secondary">
            Export includes separate sheets for Properties, Loans, and Manual NOI/Capex overrides so you can prepare everything before uploading.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Tip: Property_ID must be unique within a portfolio and is used to link loans and manual overrides.
          </Typography>
        </Box>

        <TextField
          fullWidth
          select
          label="Select Portfolio"
          value={selectedPortfolio}
          onChange={(e) => setSelectedPortfolio(e.target.value)}
          sx={{ mb: 3 }}
        >
          {portfolios.map((portfolio) => (
            <MenuItem key={portfolio.id} value={portfolio.id}>
              {portfolio.name}
            </MenuItem>
          ))}
        </TextField>

        <Box
          {...getRootProps()}
          sx={{
            border: '2px dashed',
            borderColor: isDragActive ? 'primary.main' : 'grey.400',
            borderRadius: 2,
            p: 4,
            textAlign: 'center',
            cursor: 'pointer',
            bgcolor: isDragActive ? 'action.hover' : 'background.paper',
            mb: 2
          }}
        >
          <input {...getInputProps()} />
          <CloudUploadIcon sx={{ fontSize: 60, color: 'grey.500', mb: 2 }} />
          {isDragActive ? (
            <Typography>Drop the Excel file here...</Typography>
          ) : (
            <Box>
              <Typography variant="h6" gutterBottom>
                Drag and drop an Excel file here
              </Typography>
              <Typography variant="body2" color="text.secondary">
                or click to select a file
              </Typography>
            </Box>
          )}
        </Box>

        {file && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2">
              Selected file: <strong>{file.name}</strong> ({(file.size / 1024).toFixed(2)} KB)
            </Typography>
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {result && (
          <Alert severity={result.errors && result.errors.length ? 'warning' : 'success'} sx={{ mb: 2 }}>
            <Typography variant="body1" gutterBottom>
              {result.message}
            </Typography>
            <Typography variant="body2">
              Properties created: {result.properties_created} · updated: {result.properties_updated}
            </Typography>
            <Typography variant="body2">
              Loans created: {result.loans_created} · updated: {result.loans_updated}
            </Typography>
            {result.errors && result.errors.length > 0 && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="body2" color="error">
                  Issues detected:
                </Typography>
                <List dense>
                  {result.errors.map((err, idx) => (
                    <ListItem key={idx}>
                      <ListItemText primary={err} />
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}
          </Alert>
        )}

        <Button
          variant="contained"
          fullWidth
          onClick={handleUpload}
          disabled={!file || !selectedPortfolio || uploading}
          startIcon={uploading ? <CircularProgress size={20} /> : <CloudUploadIcon />}
        >
          {uploading ? 'Uploading...' : 'Upload File'}
        </Button>
      </Paper>
    </Box>
  )
}

export default ExcelUpload
