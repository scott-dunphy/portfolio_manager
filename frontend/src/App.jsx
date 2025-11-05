import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import Box from '@mui/material/Box'
import AppBar from '@mui/material/AppBar'
import Toolbar from '@mui/material/Toolbar'
import Typography from '@mui/material/Typography'
import Container from '@mui/material/Container'

import PortfolioList from './pages/PortfolioList'
import PortfolioDetail from './pages/PortfolioDetail'
import PortfolioSetup from './pages/PortfolioSetup'
import PropertyList from './pages/PropertyList'
import PropertyForm from './pages/PropertyForm'
import LoanList from './pages/LoanList'
import LoanForm from './pages/LoanForm'
import ExcelUpload from './pages/ExcelUpload'

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
})

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <AppBar position="static">
          <Toolbar>
            <Typography variant="h6" component="div">
              Portfolio Manager
            </Typography>
          </Toolbar>
        </AppBar>
        <Container sx={{ mt: 4, mb: 4, flexGrow: 1 }}>
          <Routes>
            <Route path="/" element={<PortfolioList />} />
            <Route path="/portfolios/:portfolioId/setup" element={<PortfolioSetup />} />
            <Route path="/portfolios/:id" element={<PortfolioDetail />} />
            <Route path="/properties" element={<PropertyList />} />
            <Route path="/properties/new" element={<PropertyForm />} />
            <Route path="/properties/:id/edit" element={<PropertyForm />} />
            <Route path="/loans" element={<LoanList />} />
            <Route path="/loans/new" element={<LoanForm />} />
            <Route path="/loans/:id/edit" element={<LoanForm />} />
            <Route path="/upload" element={<ExcelUpload />} />
          </Routes>
        </Container>
      </Box>
    </ThemeProvider>
  )
}

export default App
