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
    mode: 'light',
    primary: {
      main: '#4f46e5',
      light: '#818cf8',
      dark: '#3730a3'
    },
    secondary: {
      main: '#f97316'
    },
    background: {
      default: '#f5f7fb',
      paper: '#ffffff'
    },
    text: {
      primary: '#0f172a',
      secondary: '#475467'
    }
  },
  shape: {
    borderRadius: 16
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica Neue", "Arial", sans-serif',
    h4: {
      fontWeight: 600,
      letterSpacing: '-0.5px'
    },
    h5: {
      fontWeight: 600
    },
    button: {
      textTransform: 'none',
      fontWeight: 600
    }
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#f5f7fb'
        }
      }
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: 'transparent',
          boxShadow: 'none'
        }
      }
    },
    MuiButton: {
      defaultProps: {
        disableElevation: true
      },
      styleOverrides: {
        root: {
          borderRadius: 999,
          paddingLeft: 20,
          paddingRight: 20
        }
      }
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 20,
          border: '1px solid rgba(15, 23, 42, 0.06)',
          boxShadow: '0 20px 45px rgba(15, 23, 42, 0.08)'
        }
      }
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 20
        }
      }
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          '& .MuiTableCell-root': {
            fontWeight: 600,
            color: '#0f172a',
            backgroundColor: '#eef2ff'
          }
        }
      }
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600
        }
      }
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 600,
          borderRadius: 999
        }
      }
    }
  }
})

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box
        sx={{
          minHeight: '100vh',
          backgroundImage: `
            radial-gradient(circle at 10% 20%, rgba(79, 70, 229, 0.12), transparent 35%),
            radial-gradient(circle at 80% 0%, rgba(14, 165, 233, 0.18), transparent 32%),
            linear-gradient(180deg, rgba(255, 255, 255, 0.8), rgba(245, 247, 251, 1))
          `
        }}
      >
        <AppBar position="sticky" elevation={0} color="transparent">
          <Toolbar sx={{ minHeight: 80 }}>
            <Box>
              <Typography
                variant="h6"
                sx={{ fontWeight: 700, letterSpacing: '-0.5px', color: '#a855f7' }}
              >
                Portfolio Manager
              </Typography>
            </Box>
          </Toolbar>
        </AppBar>
        <Container maxWidth="xl" sx={{ py: 4, flexGrow: 1 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, pb: 6 }}>
            <Routes>
              <Route path="/" element={<PortfolioList />} />
              <Route path="/portfolios" element={<PortfolioList />} />
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
          </Box>
        </Container>
      </Box>
    </ThemeProvider>
  )
}

export default App
