import React, { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Divider,
  FormControlLabel,
  Grid,
  IconButton,
  MenuItem,
  Switch,
  TextField,
  Paper,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Typography,
  Checkbox
} from '@mui/material'
import { ArrowBack as ArrowBackIcon } from '@mui/icons-material'
import DownloadIcon from '@mui/icons-material/Download'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown'
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp'
import Collapse from '@mui/material/Collapse'
import {
  portfolioAPI,
  propertyAPI,
  loanAPI,
  preferredEquityAPI,
  cashFlowAPI,
  propertyOwnershipAPI,
  covenantAPI
} from '../services/api'
import {
  formatCurrencyDisplay,
  formatCurrencyInputValue,
  normalizeCurrencyInput,
  sanitizeCurrencyInput
} from '../utils/numberFormat'

const PROPERTY_CURRENCY_FIELDS = new Set([
  'purchase_price',
  'market_value_start',
  'initial_noi',
  'disposition_price_override'
])

const buildPropertyFormState = (property = {}) => ({
  portfolio_id: property.portfolio_id ?? '',
  property_id: property.property_id ?? '',
  property_name: property.property_name ?? '',
  property_type: property.property_type ?? '',
  address: property.address ?? '',
  city: property.city ?? '',
  state: property.state ?? '',
  zip_code: property.zip_code ?? '',
  purchase_price: property.purchase_price != null ? String(Math.round(property.purchase_price)) : '',
  market_value_start:
    property.market_value_start != null ? String(Math.round(property.market_value_start)) : '',
  disposition_price_override:
    property.disposition_price_override != null ? String(Math.round(property.disposition_price_override)) : '',
  purchase_date: property.purchase_date || '',
  exit_date: property.exit_date || '',
  exit_cap_rate: property.exit_cap_rate ?? '',
  year_1_cap_rate: property.year_1_cap_rate ?? '',
  calculated_year1_cap_rate: property.calculated_year1_cap_rate ?? property.year_1_cap_rate ?? '',
  building_size: property.building_size ?? '',
  noi_growth_rate: property.noi_growth_rate ?? '',
  initial_noi: property.initial_noi != null ? String(Math.round(property.initial_noi)) : '',
  valuation_method: property.valuation_method || 'growth',
  ownership_percent: property.ownership_percent ?? 1,
  capex_percent_of_noi:
    property.capex_percent_of_noi != null ? String(property.capex_percent_of_noi) : '',
  encumbrance_override: Boolean(property.encumbrance_override),
  encumbrance_note: property.encumbrance_note || '',
  has_active_loan: Boolean(property.has_active_loan),
  is_encumbered: Boolean(property.is_encumbered),
  encumbrance_periods: Array.isArray(property.encumbrance_periods)
    ? property.encumbrance_periods.map((period) => ({
        start_date: period.start_date || null,
        end_date: period.end_date || null,
        manual: Boolean(period.manual),
        loan_id: period.loan_id ?? null
      }))
    : []
})

function PortfolioDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [portfolio, setPortfolio] = useState(null)
  const [properties, setProperties] = useState([])
  const [propertyForms, setPropertyForms] = useState({})
  const [propertyFormStatus, setPropertyFormStatus] = useState({})
  const [focusedPropertyCurrencyField, setFocusedPropertyCurrencyField] = useState(null)
  const [loans, setLoans] = useState([])
  const [preferredEquities, setPreferredEquities] = useState([])
  const [cashFlows, setCashFlows] = useState([])
  const [cashFlowsLoading, setCashFlowsLoading] = useState(false)
  const [cashFlowsLoaded, setCashFlowsLoaded] = useState(false)
  const [performanceData, setPerformanceData] = useState(null)
  const [performanceLoading, setPerformanceLoading] = useState(false)
  const [performanceLoaded, setPerformanceLoaded] = useState(false)
  const [performanceError, setPerformanceError] = useState('')
  const [performanceExpanded, setPerformanceExpanded] = useState({})
  const [performanceOwnership, setPerformanceOwnership] = useState(false)
  const [covenantData, setCovenantData] = useState(null)
  const [covenantLoading, setCovenantLoading] = useState(false)
  const [covenantLoaded, setCovenantLoaded] = useState(false)
  const [covenantError, setCovenantError] = useState('')
  const [covenantExpanded, setCovenantExpanded] = useState({})
  const [covenantOwnership, setCovenantOwnership] = useState(false)
  const propertyValuationMap = useMemo(() => {
    const map = new Map()
    properties.forEach((property) => {
      const entries = ((property.monthly_market_values || []).slice() || [])
        .filter((entry) => entry?.date)
        .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
        .map((entry, idx) => ({
          date: entry.date,
          market_value: entry.market_value ?? null,
          forward_noi_12m: entry.forward_noi_12m,
          cap_rate: entry.cap_rate,
          _index: idx
        }))
      const byDate = new Map(entries.map((entry) => [entry.date, entry]))
      map.set(property.id, { entries, byDate })
    })
    return map
  }, [properties])
  const [tab, setTab] = useState(0)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [ownershipEvents, setOwnershipEvents] = useState({})
  const [ownershipEventForms, setOwnershipEventForms] = useState({})
  const [applyOwnership, setApplyOwnership] = useState(false)
  const [manualCashFlowForms, setManualCashFlowForms] = useState({})
  const [manualCashFlowFocus, setManualCashFlowFocus] = useState({})
  const [propertyCashFlowExpanded, setPropertyCashFlowExpanded] = useState({})
  const [propertyFlowState, setPropertyFlowState] = useState({})
  const [loanFlowState, setLoanFlowState] = useState({})
  const [loanAccordionExpanded, setLoanAccordionExpanded] = useState({})
  const [downloadingReport, setDownloadingReport] = useState(false)
  const [manualFlowForm, setManualFlowForm] = useState({
    date: '',
    amount: '',
    type: 'capital_call',
    description: ''
  })
  const manualFlowOptions = [
    { value: 'capital_call', label: 'Capital Call (inflow)' },
    { value: 'distribution', label: 'Distribution (outflow)' },
    { value: 'redemption_payment', label: 'Redemption Payment (outflow)' }
  ]

  useEffect(() => {
    fetchPortfolioData()
    setPropertyFlowState({})
    setManualCashFlowForms({})
  }, [id])

  useEffect(() => {
    if (!properties || properties.length === 0) {
      setPropertyForms({})
      setPropertyFormStatus({})
      return
    }
    const mappedForms = {}
    properties.forEach((property) => {
      mappedForms[property.id] = buildPropertyFormState(property)
    })
    setPropertyForms(mappedForms)
    setPropertyFormStatus((prev) => {
      const statusState = {}
      properties.forEach((property) => {
        statusState[property.id] =
          prev[property.id] || {
            saving: false,
            error: '',
            success: ''
          }
      })
      return statusState
    })
  }, [properties])

  useEffect(() => {
    if (tab === 3 && !cashFlowsLoaded && !cashFlowsLoading) {
      loadPortfolioCashFlows()
    }
  }, [tab, cashFlowsLoaded, cashFlowsLoading])

  useEffect(() => {
    if (tab === 4 && !performanceLoaded && !performanceLoading) {
      loadPerformance()
    }
  }, [tab, performanceLoaded, performanceLoading])

  useEffect(() => {
    if (tab === 5 && !covenantLoaded && !covenantLoading) {
      loadCovenants()
    }
  }, [tab, covenantLoaded, covenantLoading])

  useEffect(() => {
    setPerformanceExpanded({})
  }, [performanceData])

  useEffect(() => {
    setCovenantExpanded({})
  }, [covenantData])

  const fetchPortfolioData = async () => {
    try {
      const [portfolioRes, propertiesRes, loansRes, prefEquityRes] = await Promise.all([
        portfolioAPI.getById(id),
        propertyAPI.getAll(id),
        loanAPI.getAll(id),
        preferredEquityAPI.getAll(id)
      ])
      setPortfolio(portfolioRes.data)
      const propertiesData = propertiesRes.data || []
      setProperties(propertiesData)
      setLoans(loansRes.data)
      setPreferredEquities(prefEquityRes.data)
      setCashFlows([])
      setCashFlowsLoaded(false)
      setPerformanceData(null)
      setPerformanceLoaded(false)
      setPerformanceError('')

      const eventsState = {}
      propertiesData.forEach((property) => {
        eventsState[property.id] = {
          data: property.ownership_events || [],
          loading: false,
          error: ''
        }
      })
      setOwnershipEvents(eventsState)
      setOwnershipEventForms((prev) => {
        const updated = { ...prev }
        propertiesData.forEach((property) => {
          if (!updated[property.id]) {
            updated[property.id] = {
              event_date: property.purchase_date || new Date().toISOString().split('T')[0],
              ownership_percent: property.ownership_percent ?? 1,
              note: ''
            }
          }
        })
        return updated
      })
    } catch (error) {
      console.error('Error fetching portfolio data:', error)
      setError(error.response?.data?.error || error.message || 'Failed to load portfolio.')
      setPortfolio(null)
    }
  }

  const handleDeleteProperty = async (propertyId) => {
    if (!window.confirm('Delete this property? This will remove related loans.')) {
      return
    }
    try {
      await propertyAPI.delete(propertyId)
      setSuccess('Property deleted.')
      setError('')
      await fetchPortfolioData()
    } catch (err) {
      setError('Failed to delete property: ' + (err.response?.data?.error || err.message))
      setSuccess('')
    }
  }

  const getPropertyFormValues = (propertyId) => {
    if (propertyForms[propertyId]) {
      return propertyForms[propertyId]
    }
    const property = properties.find((prop) => prop.id === propertyId)
    return buildPropertyFormState(property || {})
  }

  const getPropertyFieldValue = (propertyId, field) => {
    const values = getPropertyFormValues(propertyId)
    return values[field] ?? ''
  }

  const getPropertyCurrencyValue = (propertyId, field) => {
    const rawValue = getPropertyFieldValue(propertyId, field)
    const focusKey = `${propertyId}:${field}`
    if (focusedPropertyCurrencyField === focusKey) {
      return rawValue
    }
    return formatCurrencyInputValue(rawValue)
  }

  const handlePropertyFieldChange = (propertyId, field, value) => {
    const nextValue = PROPERTY_CURRENCY_FIELDS.has(field) ? sanitizeCurrencyInput(value) : value
    setPropertyForms((prev) => {
      const current =
        prev[propertyId] ||
        buildPropertyFormState(properties.find((prop) => prop.id === propertyId) || {})
      return {
        ...prev,
        [propertyId]: {
          ...current,
          [field]: nextValue
        }
      }
    })
    setPropertyFormStatus((prev) => {
      const status = prev[propertyId] || { saving: false, error: '', success: '' }
      return {
        ...prev,
        [propertyId]: {
          ...status,
          error: '',
          success: ''
        }
      }
    })
  }

  const handlePropertyFormReset = (propertyId) => {
    const property = properties.find((prop) => prop.id === propertyId)
    if (!property) {
      return
    }
    setPropertyForms((prev) => ({
      ...prev,
      [propertyId]: buildPropertyFormState(property)
    }))
    setPropertyFormStatus((prev) => {
      const status = prev[propertyId] || { saving: false, error: '', success: '' }
      return {
        ...prev,
        [propertyId]: {
          ...status,
          error: '',
          success: ''
        }
      }
    })
  }

  const handlePropertyEncumbranceOverrideChange = (propertyId, checked) => {
    const hasActiveLoan = Boolean(getPropertyFieldValue(propertyId, 'has_active_loan'))
    if (hasActiveLoan) {
      return
    }
    handlePropertyFieldChange(propertyId, 'encumbrance_override', checked)
    if (!checked) {
      handlePropertyFieldChange(propertyId, 'encumbrance_note', '')
    }
  }

  const handleSaveProperty = async (propertyId) => {
    const values = getPropertyFormValues(propertyId)
    if (values.encumbrance_override && !(values.encumbrance_note || '').trim()) {
      setPropertyFormStatus((prev) => ({
        ...prev,
        [propertyId]: {
          ...(prev[propertyId] || { saving: false, error: '', success: '' }),
          saving: false,
          error: 'Encumbrance note is required when manual encumbrance is selected.',
          success: ''
        }
      }))
      return
    }
    setPropertyFormStatus((prev) => ({
      ...prev,
      [propertyId]: {
        ...(prev[propertyId] || { saving: false, error: '', success: '' }),
        saving: true,
        error: '',
        success: ''
      }
    }))
    try {
      const {
        calculated_year1_cap_rate: _calculatedYear1CapRate,
        has_active_loan: _hasActiveLoan,
        is_encumbered: _isEncumbered,
        ...rest
      } = values
      const payload = {
        ...rest,
        purchase_price: values.purchase_price ? Number(values.purchase_price) : null,
        market_value_start: values.market_value_start ? Number(values.market_value_start) : null,
        initial_noi: values.initial_noi ? Number(values.initial_noi) : null,
        capex_percent_of_noi:
          values.capex_percent_of_noi === '' ? null : Number(values.capex_percent_of_noi),
        disposition_price_override:
          values.disposition_price_override === ''
            ? null
            : Number(values.disposition_price_override),
        encumbrance_override: Boolean(values.encumbrance_override),
        encumbrance_note: values.encumbrance_override
          ? (values.encumbrance_note || '').trim()
          : null
      }
      await propertyAPI.update(propertyId, payload)
      await fetchPortfolioData()
      setPropertyFormStatus((prev) => ({
        ...prev,
        [propertyId]: {
          ...(prev[propertyId] || { saving: false, error: '', success: '' }),
          saving: false,
          error: '',
          success: 'Property updated.'
        }
      }))
      setSuccess('Property updated.')
      setError('')
    } catch (err) {
      console.error('Failed to update property:', err)
      setPropertyFormStatus((prev) => ({
        ...prev,
        [propertyId]: {
          ...(prev[propertyId] || { saving: false, error: '', success: '' }),
          saving: false,
          error: err.response?.data?.error || err.message || 'Failed to update property.',
          success: ''
        }
      }))
    }
  }

  const parseISODate = React.useCallback((value) => {
    if (!value) {
      return null
    }
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? null : date
  }, [])

  const isPropertyEncumberedOnDate = React.useCallback(
    (propertyId, isoDate) => {
      const values = getPropertyFormValues(propertyId)
      if (!values || !isoDate) {
        return false
      }
      if (values.encumbrance_override) {
        return true
      }
      const targetDate = parseISODate(isoDate)
      if (!targetDate) {
        return false
      }
      const periods = Array.isArray(values.encumbrance_periods)
        ? values.encumbrance_periods
        : []
      return periods.some((period) => {
        if (period.manual) {
          return true
        }
        const start = parseISODate(period.start_date)
        const end = parseISODate(period.end_date)
        if (!start || !end) {
          return false
        }
        return start <= targetDate && targetDate <= end
      })
    },
    [getPropertyFormValues, parseISODate]
  )

  const handleDeleteLoan = async (loanId) => {
    if (!window.confirm('Delete this loan?')) {
      return
    }
    try {
      await loanAPI.delete(loanId)
      setSuccess('Loan deleted.')
      setError('')
      await fetchPortfolioData()
    } catch (err) {
      setError('Failed to delete loan: ' + (err.response?.data?.error || err.message))
      setSuccess('')
    }
  }

  const handleDeletePreferredEquity = async (prefId) => {
    if (!window.confirm('Delete this preferred equity investment?')) {
      return
    }
    try {
      await preferredEquityAPI.delete(prefId)
      setSuccess('Preferred equity deleted.')
      setError('')
      await fetchPortfolioData()
    } catch (err) {
      setError('Failed to delete preferred equity: ' + (err.response?.data?.error || err.message))
      setSuccess('')
    }
  }

  const propertyMap = useMemo(
    () => new Map(properties.map((property) => [property.id, property])),
    [properties]
  )
  const loanMap = useMemo(
    () => new Map(loans.map((loan) => [loan.id, loan])),
    [loans]
  )
  const cashFlowTypes = useMemo(() => {
    const types = new Set()
    let hasUncategorized = false
    cashFlows.forEach((cf) => {
      if (cf.cash_flow_type) {
        types.add(cf.cash_flow_type)
      } else {
        hasUncategorized = true
      }
    })
    if (hasUncategorized) {
      types.add('Uncategorized')
    }
    return Array.from(types).sort()
  }, [cashFlows])
  const [dateExpanded, setDateExpanded] = useState({})
  const [propertyExpanded, setPropertyExpanded] = useState({})
  const toggleDateRow = (dateKey) => {
    setDateExpanded((prev) => ({
      ...prev,
      [dateKey]: !prev[dateKey]
    }))
  }
  const togglePropertyRow = (key) => {
    setPropertyExpanded((prev) => ({
      ...prev,
      [key]: !prev[key]
    }))
  }

  const getOwnershipPercentForDate = useMemo(() => {
    const cache = new Map()

    return (propertyId, isoDate) => {
      if (!propertyId) return 1

      const cacheKey = `${propertyId}|${isoDate || 'all'}|${applyOwnership}`
      if (cache.has(cacheKey)) {
        return cache.get(cacheKey)
      }

      let percent = 1
      try {
        const events =
          ownershipEvents[propertyId]?.data ||
          propertyMap.get(propertyId)?.ownership_events ||
          []

        if (!events.length) {
          percent = propertyMap.get(propertyId)?.ownership_percent ?? 1
        } else {
          const targetTime = isoDate ? new Date(isoDate).getTime() : Number.POSITIVE_INFINITY
          percent = events[0]?.ownership_percent ?? 1
          for (const event of events) {
            if (!event?.event_date) continue
            const eventTime = new Date(event.event_date).getTime()
            if (eventTime <= targetTime) {
              percent = event.ownership_percent ?? percent
            } else {
              break
            }
          }
        }
      } catch (err) {
        console.error('Failed to derive ownership percent', err)
        percent = 1
      }

      if (typeof percent !== 'number' || !Number.isFinite(percent)) {
        percent = 1
      }

      cache.set(cacheKey, percent)
      return percent
    }
  }, [ownershipEvents, propertyMap, applyOwnership])

  const handleManualFlowInputChange = (e) => {
    const raw = e.target.value.replace(/,/g, '')
    if (/^\d*$/.test(raw)) {
      setManualFlowForm((prev) => ({
        ...prev,
        amount: raw
      }))
    }
  }

  const handleManualFlowAmountBlur = () => {
    setManualFlowForm((prev) => ({
      ...prev,
      amount: formatCurrencyInputValue(prev.amount)
    }))
  }

  const handleManualFlowFieldChange = (field, value) => {
    setManualFlowForm((prev) => ({
      ...prev,
      [field]: value
    }))
  }

  const handleManualFlowSubmit = async (e) => {
    e.preventDefault()
    if (!manualFlowForm.date) {
      setError('Please select a date for the cash flow.')
      return
    }
    const normalizedAmount = normalizeCurrencyInput(manualFlowForm.amount)
    const amountValue = parseFloat(normalizedAmount)
    if (!Number.isFinite(amountValue)) {
      setError('Please enter a valid amount.')
      return
    }

    let signedAmount = Math.abs(amountValue)
    if (manualFlowForm.type === 'distribution' || manualFlowForm.type === 'redemption_payment') {
      signedAmount = -signedAmount
    }

    try {
      await cashFlowAPI.create({
        portfolio_id: id,
        property_id: null,
        loan_id: null,
        date: manualFlowForm.date,
        cash_flow_type: manualFlowForm.type,
        amount: signedAmount,
        description: manualFlowForm.description
      })
      setSuccess('Cash flow recorded.')
      setError('')
      setManualFlowForm({
        date: '',
        amount: '',
        type: manualFlowForm.type,
        description: ''
      })
      await fetchPortfolioData()
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to save cash flow.')
    }
  }

  const manualFocusKey = (propertyId, index, field) => `${propertyId}-${index}-${field}`

  const getManualState = (propertyId) =>
    manualCashFlowForms[propertyId] || { rows: [], loading: false, error: '', loaded: false }
  const getManualRows = (propertyId) => getManualState(propertyId).rows

  const handleManualRowChange = (propertyId, index, field, value) => {
    setManualCashFlowForms((prev) => {
      const prevState = prev[propertyId] || { rows: [], loading: false, error: '', loaded: false }
      const rows = [...prevState.rows]
      const existing = rows[index] || {
        year: '',
        frequency: 'annual',
        month: '',
        annual_noi: '',
        annual_capex: ''
      }
      const updatedRow = { ...existing }

      if (field === 'year') {
        updatedRow.year = value.replace(/[^0-9]/g, '')
      } else if (field === 'frequency') {
        updatedRow.frequency = value
        if (value === 'monthly' && !updatedRow.month) {
          updatedRow.month = '1'
        }
        if (value !== 'monthly') {
          updatedRow.month = ''
        }
      } else if (field === 'month') {
        const digits = value.replace(/[^0-9]/g, '')
        if (digits === '') {
          updatedRow.month = ''
        } else {
          let monthValue = Number(digits)
          if (Number.isNaN(monthValue)) {
            updatedRow.month = ''
          } else {
            monthValue = Math.max(1, Math.min(12, monthValue))
            updatedRow.month = String(monthValue)
          }
        }
      } else if (field === 'annual_noi' || field === 'annual_capex') {
        updatedRow[field] = sanitizeCurrencyInput(value)
      } else {
        updatedRow[field] = value
      }

      rows[index] = updatedRow
      return {
        ...prev,
        [propertyId]: { ...prevState, rows, loaded: true }
      }
    })
  }

  const handleManualFieldFocus = (propertyId, index, field) => {
    setManualCashFlowFocus((prev) => ({
      ...prev,
      [manualFocusKey(propertyId, index, field)]: true
    }))
  }

  const handleManualFieldBlur = (propertyId, index, field) => {
    const key = manualFocusKey(propertyId, index, field)
    setManualCashFlowFocus((prev) => {
      const updated = { ...prev }
      delete updated[key]
      return updated
    })
    if (field === 'annual_noi' || field === 'annual_capex') {
      setManualCashFlowForms((prev) => {
        const prevState = prev[propertyId] || { rows: [], loading: false, error: '', loaded: false }
        const rows = [...prevState.rows]
        if (!rows[index]) return prev
        const normalized = normalizeCurrencyInput(rows[index][field])
        rows[index] = { ...rows[index], [field]: normalized }
        return {
          ...prev,
          [propertyId]: { ...prevState, rows }
        }
      })
    }
  }

  const displayManualValue = (propertyId, index, field, value) => {
    const key = manualFocusKey(propertyId, index, field)
    if (field === 'year' || field === 'month' || field === 'frequency') {
      return value
    }
    return manualCashFlowFocus[key] ? value : formatCurrencyInputValue(value)
  }

  const handleManualAddRow = (propertyId) => {
    const manualState = getManualState(propertyId)
    if (!manualState.loaded) {
      if (!manualState.loading) {
        loadManualCashFlows(propertyId)
      }
      return
    }
    setManualCashFlowForms((prev) => {
      const prevState = prev[propertyId] || { rows: [], loading: false, error: '', loaded: false }
      const rows = [...prevState.rows]
      const lastYear = rows.length ? rows[rows.length - 1].year : ''
      const nextYear = lastYear ? String(Number(lastYear) + 1) : ''
      rows.push({
        year: nextYear,
        frequency: 'annual',
        month: '',
        annual_noi: '',
        annual_capex: ''
      })
      return {
        ...prev,
        [propertyId]: { ...prevState, rows, loaded: true }
      }
    })
  }

  const handleManualRemoveRow = (propertyId, index) => {
    const manualState = getManualState(propertyId)
    if (!manualState.loaded) {
      if (!manualState.loading) {
        loadManualCashFlows(propertyId)
      }
      return
    }
    setManualCashFlowForms((prev) => {
      const prevState = prev[propertyId] || { rows: [], loading: false, error: '', loaded: false }
      const rows = [...prevState.rows]
      rows.splice(index, 1)
      return {
        ...prev,
        [propertyId]: { ...prevState, rows, loaded: true }
      }
    })
  }

  const handleManualPrefillRows = (propertyId, property) => {
    const manualState = getManualState(propertyId)
    if (!manualState.loaded) {
      if (!manualState.loading) {
        loadManualCashFlows(propertyId)
      }
      return
    }
    if (!portfolio) return
    const fallbackYear = property.purchase_date
      ? new Date(property.purchase_date).getFullYear()
      : new Date().getFullYear()
    const startYear = portfolio.analysis_start_date
      ? new Date(portfolio.analysis_start_date).getFullYear()
      : fallbackYear
    const endYear = portfolio.analysis_end_date
      ? new Date(portfolio.analysis_end_date).getFullYear()
      : startYear + 4
    const existing = getManualRows(propertyId)
    const rows = []
    for (let year = startYear; year <= endYear; year += 1) {
      const match = existing.find((row) => Number(row.year) === year)
      rows.push({
        year: String(year),
        frequency: match?.frequency || 'annual',
        month: match?.month || '',
        annual_noi: match?.annual_noi || '',
        annual_capex: match?.annual_capex || ''
      })
    }
    setManualCashFlowForms((prev) => ({
      ...prev,
      [propertyId]: { rows, loading: false, error: '', loaded: true }
    }))
  }

  const handleManualToggle = async (propertyId, enabled) => {
    try {
      await propertyAPI.update(propertyId, { use_manual_noi_capex: enabled })
      setSuccess(enabled ? 'Manual NOI & Capex enabled.' : 'Manual NOI & Capex disabled.')
      setError('')
      setProperties((prev) =>
        prev.map((property) =>
          property.id === propertyId ? { ...property, use_manual_noi_capex: enabled } : property
        )
      )
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to update manual mode.')
      setSuccess('')
    }
  }

  const handleManualSave = async (propertyId, property) => {
    const manualState = getManualState(propertyId)
    if (!manualState.loaded) {
      if (!manualState.loading) {
        loadManualCashFlows(propertyId)
      }
      setError('Manual entries are still loading. Please try again once they finish loading.')
      return
    }

    const rows = manualState.rows
    const entries = []

    for (const row of rows) {
      if (!row.year) continue
      const freq = row.frequency || 'annual'
      if (freq === 'monthly' && !row.month) {
        setError('Monthly manual entries require a month (1-12).')
        return
      }
      const normalizedNoi = normalizeCurrencyInput(row.annual_noi)
      const normalizedCapex = normalizeCurrencyInput(row.annual_capex)
      entries.push({
        year: Number(row.year),
        month: freq === 'monthly' ? Number(row.month) : null,
        annual_noi: normalizedNoi === '' ? null : Number(normalizedNoi),
        annual_capex: normalizedCapex === '' ? null : Number(normalizedCapex)
      })
    }

    try {
      await propertyAPI.saveManualCashFlows(propertyId, {
        entries,
        use_manual_noi_capex: property.use_manual_noi_capex
      })
      setSuccess('Manual NOI & Capex saved.')
      setError('')
      await loadManualCashFlows(propertyId)
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to save manual cash flows.')
      setSuccess('')
    }
  }

  const loadManualCashFlows = async (propertyId) => {
    setManualCashFlowForms((prev) => {
      const prevState = prev[propertyId] || { rows: [], loading: false, error: '', loaded: false }
      return {
        ...prev,
        [propertyId]: { ...prevState, loading: true, error: '' }
      }
    })
    try {
      const response = await propertyAPI.getManualCashFlows(propertyId)
      const rows = (response.data || []).map((entry) => ({
        year: entry.year != null ? String(entry.year) : '',
        month: entry.month != null ? String(entry.month) : '',
        frequency: entry.month ? 'monthly' : 'annual',
        annual_noi: entry.annual_noi != null ? String(Math.round(entry.annual_noi)) : '',
        annual_capex: entry.annual_capex != null ? String(Math.round(entry.annual_capex)) : ''
      }))
      setManualCashFlowForms((prev) => ({
        ...prev,
        [propertyId]: { rows, loading: false, error: '', loaded: true }
      }))
    } catch (err) {
      setManualCashFlowForms((prev) => {
        const prevState = prev[propertyId] || { rows: [], loading: false, error: '', loaded: false }
        return {
          ...prev,
          [propertyId]: {
            ...prevState,
            loading: false,
            error: err.response?.data?.error || err.message || 'Failed to load manual entries'
          }
        }
      })
    }
  }

  const loadPropertyCashFlows = async (propertyId) => {
    setPropertyFlowState((prev) => ({
      ...prev,
      [propertyId]: {
        ...(prev[propertyId] || {}),
        loading: true,
        error: '',
        data: prev[propertyId]?.data || []
      }
    }))
    try {
      const response = await cashFlowAPI.getAll({ propertyId })
      setPropertyFlowState((prev) => ({
        ...prev,
        [propertyId]: {
          loading: false,
          error: '',
          data: response.data || []
        }
      }))
    } catch (err) {
      setPropertyFlowState((prev) => ({
        ...prev,
        [propertyId]: {
          ...(prev[propertyId] || {}),
          loading: false,
          error: err.response?.data?.error || err.message || 'Failed to load cash flows',
          data: prev[propertyId]?.data || []
        }
      }))
    }
  }

  const loadPortfolioCashFlows = async () => {
    setCashFlowsLoading(true)
    setError('')
    try {
      const response = await cashFlowAPI.getAll({ portfolioId: id })
      setCashFlows(response.data || [])
      setCashFlowsLoaded(true)
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to load portfolio cash flows.')
    } finally {
      setCashFlowsLoading(false)
    }
  }

  const loadPerformance = async (ownershipFlag = performanceOwnership) => {
    setPerformanceLoading(true)
    setPerformanceError('')
    try {
      const response = await cashFlowAPI.getPerformance(id, ownershipFlag)
      setPerformanceData(response.data || { quarters: [] })
      setPerformanceLoaded(true)
    } catch (err) {
      setPerformanceError(err.response?.data?.error || err.message || 'Failed to load performance.')
    } finally {
      setPerformanceLoading(false)
    }
  }

  const togglePerformanceRow = (label) => {
    setPerformanceExpanded((prev) => ({
      ...prev,
      [label]: !prev[label]
    }))
  }

  const handlePerformanceOwnershipToggle = async (event) => {
    const nextValue = event.target.checked
    setPerformanceOwnership(nextValue)
    setPerformanceLoaded(false)
    await loadPerformance(nextValue)
  }

  const loadCovenants = async (ownershipFlag = covenantOwnership) => {
    setCovenantLoading(true)
    setCovenantError('')
    try {
      const response = await covenantAPI.getMetrics(id, ownershipFlag)
      setCovenantData(response.data || { months: [] })
      setCovenantLoaded(true)
    } catch (err) {
      setCovenantError(err.response?.data?.error || err.message || 'Failed to load covenants.')
    } finally {
      setCovenantLoading(false)
    }
  }

  const toggleCovenantRow = (label) => {
    setCovenantExpanded((prev) => ({
      ...prev,
      [label]: !prev[label]
    }))
  }

  const handleCovenantOwnershipToggle = async (event) => {
    const nextValue = event.target.checked
    setCovenantOwnership(nextValue)
    setCovenantLoaded(false)
    await loadCovenants(nextValue)
  }

  const handleDownloadCashFlowReport = async () => {
    setDownloadingReport(true)
    try {
      const response = await cashFlowAPI.downloadReport(id)
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = blobUrl
      link.setAttribute('download', `portfolio_${id}_cash_flows.xlsx`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(blobUrl)
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to download cash flows.')
    } finally {
      setDownloadingReport(false)
    }
  }

  const loadLoanCashFlows = async (loanId) => {
    setLoanFlowState((prev) => ({
      ...prev,
      [loanId]: {
        ...(prev[loanId] || {}),
        loading: true,
        error: '',
        data: prev[loanId]?.data || []
      }
    }))

    try {
      const response = await cashFlowAPI.getAll({ loanId })
      setLoanFlowState((prev) => ({
        ...prev,
        [loanId]: {
          loading: false,
          error: '',
          data: response.data || []
        }
      }))
    } catch (err) {
      setLoanFlowState((prev) => ({
        ...prev,
        [loanId]: {
          ...(prev[loanId] || {}),
          loading: false,
          error: err.response?.data?.error || err.message || 'Failed to load loan cash flows',
          data: prev[loanId]?.data || []
        }
      }))
    }
  }

  const isPropertyCashFlowOpen = (propertyId) =>
    propertyCashFlowExpanded[propertyId] ?? false

  const togglePropertyCashFlowSection = (propertyId) => {
    const nextValue = !(propertyCashFlowExpanded[propertyId] ?? false)
    setPropertyCashFlowExpanded((prev) => ({
      ...prev,
      [propertyId]: nextValue
    }))

    if (
      nextValue &&
      !propertyFlowState[propertyId]?.data &&
      !propertyFlowState[propertyId]?.loading
    ) {
      loadPropertyCashFlows(propertyId)
    }
  }

  const getPropertyValuationSnapshot = React.useCallback(
    (propertyId, isoDate) => {
      if (!propertyId || !isoDate) {
        return { current: null, prior: null }
      }
      const state = propertyValuationMap.get(propertyId)
      if (!state) {
        return { current: null, prior: null }
      }
      let current = state.byDate.get(isoDate)
      let index = current?._index
      if (!current) {
        for (let i = state.entries.length - 1; i >= 0; i -= 1) {
          if (state.entries[i].date <= isoDate) {
            current = state.entries[i]
            index = i
            break
          }
        }
      }
      if (!current) {
        return { current: null, prior: null }
      }
      const prior = index > 0 ? state.entries[index - 1] : null
      return { current, prior }
    },
    [propertyValuationMap]
  )

  const aggregatedByDate = useMemo(() => {
    const byDate = new Map()
    cashFlows.forEach((cf) => {
      const amount = cf.amount || 0
      const ownershipShareRaw =
        applyOwnership && cf.property_id
          ? getOwnershipPercentForDate(cf.property_id, cf.date)
          : 1
      const ownershipShare =
        typeof ownershipShareRaw === 'number' && Number.isFinite(ownershipShareRaw)
          ? ownershipShareRaw
          : 1
      const adjustedAmount = amount * ownershipShare
      const dateKey = cf.date
      if (!byDate.has(dateKey)) {
        byDate.set(dateKey, {
          date: dateKey,
          total: 0,
          typeTotals: {},
          properties: new Map()
        })
      }
      const entry = byDate.get(dateKey)
      entry.total += adjustedAmount
      const typeKey = cf.cash_flow_type || 'Uncategorized'
      entry.typeTotals[typeKey] = (entry.typeTotals[typeKey] || 0) + adjustedAmount

      const propertyKey = cf.property_id ?? '__unassigned__'
      if (!entry.properties.has(propertyKey)) {
        entry.properties.set(propertyKey, {
          propertyId: cf.property_id ?? null,
          total: 0,
          typeTotals: {},
          flows: []
        })
      }
      const propertyEntry = entry.properties.get(propertyKey)
      propertyEntry.total += adjustedAmount
      propertyEntry.typeTotals[typeKey] = (propertyEntry.typeTotals[typeKey] || 0) + adjustedAmount
      propertyEntry.flows.push({ ...cf, adjusted_amount: adjustedAmount })
    })

    const sorted = Array.from(byDate.values()).sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    )

    const portfolioBeginning = portfolio?.beginning_cash ?? 0
    let runningBeginning = portfolioBeginning

    return sorted.map((entry) => {
      const propertiesArray = Array.from(entry.properties.values()).map((propertyEntry) => {
        const propertyId = propertyEntry.propertyId
        const valuations = propertyId ? getPropertyValuationSnapshot(propertyId, entry.date) : { current: null, prior: null }
        const ownershipShareRaw =
          applyOwnership && propertyId
            ? getOwnershipPercentForDate(propertyId, entry.date)
            : 1
        const ownershipShare =
          typeof ownershipShareRaw === 'number' && Number.isFinite(ownershipShareRaw)
            ? ownershipShareRaw
            : 1
        const currentValueRaw = valuations.current?.market_value ?? null
        const priorValueRaw = valuations.prior?.market_value ?? null
        const currentValue =
          currentValueRaw != null ? currentValueRaw * ownershipShare : currentValueRaw
        const priorValue =
          priorValueRaw != null ? priorValueRaw * ownershipShare : priorValueRaw
        const capexRaw = propertyEntry.typeTotals['property_capex'] || 0
        const capexOutlay = -capexRaw
        const acquisitionRaw = propertyEntry.typeTotals['property_acquisition'] || 0
        const acquisitionOutlay = -acquisitionRaw
        const acquisitionOverride =
          acquisitionOutlay > 0 ? acquisitionOutlay : null
        const appreciation =
          currentValue != null && priorValue != null
            ? (acquisitionOverride ?? currentValue) - priorValue - (capexOutlay || 0) - (acquisitionOutlay || 0)
            : null
        const encumberedOnDate =
          propertyId != null ? isPropertyEncumberedOnDate(propertyId, entry.date) : false
        return {
          ...propertyEntry,
          ownershipShare,
          marketValueCurrent: acquisitionOverride ?? currentValue,
          marketValuePrior: priorValue,
          appreciation,
          encumberedOnDate,
          flows: propertyEntry.flows
            .slice()
            .sort((a, b) => (a.cash_flow_type || '').localeCompare(b.cash_flow_type || ''))
        }
      })

      propertiesArray.sort((a, b) => {
        const aRecord = propertyMap.get(a.propertyId)
        const bRecord = propertyMap.get(b.propertyId)
        const nameA =
          aRecord?.property_name ||
          aRecord?.property_id ||
          (a.propertyId ? `Property #${a.propertyId}` : 'Unassigned')
        const nameB =
          bRecord?.property_name ||
          bRecord?.property_id ||
          (b.propertyId ? `Property #${b.propertyId}` : 'Unassigned')
        return nameA.localeCompare(nameB)
      })

      const totalMarketCurrent = propertiesArray.reduce(
        (sum, item) => sum + (item.marketValueCurrent ?? 0),
        0
      )
      const totalMarketPrior = propertiesArray.reduce(
        (sum, item) => sum + (item.marketValuePrior ?? 0),
        0
      )
      const totalAppreciation = propertiesArray.reduce(
        (sum, item) => sum + (item.appreciation ?? 0),
        0
      )

      const entryWithBalances = {
        ...entry,
        properties: propertiesArray,
        beginning_cash: runningBeginning,
        ending_cash: runningBeginning + entry.total,
        market_value_current: propertiesArray.length ? totalMarketCurrent : null,
        market_value_prior: propertiesArray.length ? totalMarketPrior : null,
        appreciation_total: propertiesArray.length ? totalAppreciation : null
      }

      runningBeginning = entryWithBalances.ending_cash

      return entryWithBalances
    })
  }, [
    cashFlows,
    propertyMap,
    applyOwnership,
    ownershipEvents,
    getOwnershipPercentForDate,
    portfolio,
    getPropertyValuationSnapshot,
    isPropertyEncumberedOnDate
  ])

  const getLatestOwnershipPercent = (propertyId) => {
    const events = ownershipEvents[propertyId]?.data
    if (events && events.length) {
      return events[events.length - 1].ownership_percent
    }
    return undefined
  }


  const ensureOwnershipFormDefaults = (propertyId, property) => {
    setOwnershipEventForms((prev) => {
      if (prev[propertyId]) {
        return prev
      }
      const defaultDate =
        property?.purchase_date ||
        new Date().toISOString().split('T')[0]
      return {
        ...prev,
        [propertyId]: {
          event_date: defaultDate,
          ownership_percent: property?.ownership_percent ?? 1,
          note: ''
        }
      }
    })
  }

  const fetchOwnershipEvents = async (propertyId) => {
    setOwnershipEvents((prev) => ({
      ...prev,
      [propertyId]: {
        ...(prev[propertyId] || {}),
        loading: true,
        error: ''
      }
    }))
    try {
      const response = await propertyOwnershipAPI.getAll(propertyId)
      const events = response.data || []
      setOwnershipEvents((prev) => ({
        ...prev,
        [propertyId]: {
          data: events,
          loading: false,
          error: ''
        }
      }))

      const latestPercent = events.length ? events[events.length - 1].ownership_percent : null
      setProperties((prev) =>
        prev.map((property) =>
          property.id === propertyId
            ? { ...property, ownership_percent: latestPercent }
            : property
        )
      )
    } catch (err) {
      setOwnershipEvents((prev) => ({
        ...prev,
        [propertyId]: {
          ...(prev[propertyId] || {}),
          loading: false,
          error: err.response?.data?.error || err.message || 'Failed to load ownership history'
        }
      }))
    }
  }

  const handlePropertyAccordionChange = (propertyId, property) => (_, expanded) => {
    if (!expanded) return
    if (!ownershipEvents[propertyId] || ownershipEvents[propertyId].data.length === 0) {
      fetchOwnershipEvents(propertyId)
    }
    ensureOwnershipFormDefaults(propertyId, property)
    if (!propertyFlowState[propertyId]?.data && !propertyFlowState[propertyId]?.loading) {
      loadPropertyCashFlows(propertyId)
    }
    const manualState = manualCashFlowForms[propertyId]
    if (!manualState || (!manualState.loaded && !manualState.loading)) {
      loadManualCashFlows(propertyId)
    }
  }

  const handleLoanAccordionChange = (loanId) => (_, expanded) => {
    setLoanAccordionExpanded((prev) => ({
      ...prev,
      [loanId]: expanded
    }))
    if (expanded && !loanFlowState[loanId]?.data && !loanFlowState[loanId]?.loading) {
      loadLoanCashFlows(loanId)
    }
  }

  const handleOwnershipFormChange = (propertyId, field, value) => {
    setOwnershipEventForms((prev) => ({
      ...prev,
      [propertyId]: {
        ...(prev[propertyId] || { event_date: '', ownership_percent: '', note: '' }),
        [field]: value
      }
    }))
  }

  const handleAddOwnershipEvent = async (propertyId) => {
    const form = ownershipEventForms[propertyId]
    if (!form || !form.event_date || form.ownership_percent === '' || form.ownership_percent === null) {
      setError('Ownership event requires a date and percentage.')
      return
    }
    const percentValue = parseFloat(form.ownership_percent)
    if (!Number.isFinite(percentValue)) {
      setError('Ownership percentage must be a valid number.')
      return
    }

    setError('')
    try {
      await propertyOwnershipAPI.create(propertyId, {
        event_date: form.event_date,
        ownership_percent: percentValue,
        note: form.note
      })
      setSuccess('Ownership event saved.')
      await fetchOwnershipEvents(propertyId)
      setOwnershipEventForms((prev) => ({
        ...prev,
        [propertyId]: {
          ...form,
          ownership_percent: percentValue,
          note: ''
        }
      }))
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to save ownership event.')
    }
  }

  const handleDeleteOwnershipEvent = async (propertyId, eventId) => {
    if (!window.confirm('Delete this ownership event?')) {
      return
    }
    setError('')
    try {
      await propertyOwnershipAPI.delete(propertyId, eventId)
      setSuccess('Ownership event deleted.')
      await fetchOwnershipEvents(propertyId)
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to delete ownership event.')
    }
  }

  const formatCurrency = (value) => {
    const formatted = formatCurrencyDisplay(value)
    if (formatted === '—') {
      return formatted
    }
    return `$${formatted}`
  }

  const formatDisplayDate = (value) => {
    if (!value) return '—'
    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) {
      return value
    }
    return parsed.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  const formatDayCount = (value) => {
    if (!value) return '30/360'
    const normalized = value.toLowerCase()
    if (normalized === 'actual/360') return 'Actual/360'
    if (normalized === 'actual/365') return 'Actual/365'
    return '30/360'
  }
  const loanFlowTypePriority = {
    loan_principal: 0,
    loan_interest: 1,
    loan_funding: 2
  }
  const sortLoanFlows = (flows = []) => {
    return [...flows].sort((a, b) => {
      const rawTimeA = a.date ? new Date(a.date).getTime() : 0
      const rawTimeB = b.date ? new Date(b.date).getTime() : 0
      const timeA = Number.isFinite(rawTimeA) ? rawTimeA : 0
      const timeB = Number.isFinite(rawTimeB) ? rawTimeB : 0
      if (timeA !== timeB) {
        return timeA - timeB
      }
      const weightA = loanFlowTypePriority[a.cash_flow_type] ?? 99
      const weightB = loanFlowTypePriority[b.cash_flow_type] ?? 99
      if (weightA !== weightB) {
        return weightA - weightB
      }
      const idA = a.id ?? 0
      const idB = b.id ?? 0
      return idA - idB
    })
  }
  const formatLoanRateLabel = (loan) => {
    if (!loan) return '—'
    const dayCountLabel = formatDayCount(loan.interest_day_count)
    let rateLabel = '—'
    if (loan.rate_type === 'floating') {
      const spread = loan.sofr_spread != null ? (loan.sofr_spread * 100).toFixed(2) : '0.00'
      rateLabel = `SOFR + ${spread}%`
    } else if (loan.interest_rate != null) {
      rateLabel = `${(loan.interest_rate * 100).toFixed(2)}%`
    }
    return `${rateLabel} · ${dayCountLabel}`
  }
  const formatPercent = (value) => {
    if (value == null || value === '') return '—'
    return `${(Number(value) * 100).toFixed(2)}%`
  }
  const formatRatio = (value, digits = 2) => {
    if (value == null || value === '') return '—'
    const num = Number(value)
    if (!Number.isFinite(num)) return '—'
    return num.toFixed(digits)
  }

  const renderFloatingRate = (flow) => {
    const info = flow.floating_rate_data
    if (!info || (info.sofr_rate == null && info.total_rate == null)) {
      return '—'
    }
    const sofrText = formatPercent(info.sofr_rate)
    const spreadText =
      info.spread != null && info.spread !== 0 ? formatPercent(info.spread) : null
    const totalText =
      info.total_rate != null ? formatPercent(info.total_rate) : null

    if (spreadText && totalText) {
      return `${sofrText} + ${spreadText} = ${totalText}`
    }
    return sofrText
  }

  if (!portfolio) {
    return (
      <Box sx={{ p: 3 }}>
        {error ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        ) : (
          <Typography>Loading...</Typography>
        )}
      </Box>
    )
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/')}>
            Back
          </Button>
          <Typography variant="h4" sx={{ ml: 2 }}>
            {portfolio.name}
          </Typography>
        </Box>
        <Button
          variant="outlined"
          onClick={() => navigate(`/portfolios/${id}/property-type-exposure`)}
          sx={{ whiteSpace: 'nowrap' }}
        >
          Property Type Exposure
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>
          {success}
        </Alert>
      )}

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
            <Typography>{formatCurrency(portfolio.beginning_cash)}</Typography>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Typography variant="subtitle2" color="text.secondary">Beginning NAV</Typography>
            <Typography>{formatCurrency(portfolio.beginning_nav)}</Typography>
          </Grid>
        </Grid>
      </Paper>

      <Paper sx={{ mb: 3 }}>
        <Tabs value={tab} onChange={(e, v) => setTab(v)}>
          <Tab label={`Properties (${properties.length})`} />
          <Tab label={`Loans (${loans.length})`} />
          <Tab label={`Preferred Equity (${preferredEquities.length})`} />
          <Tab label={`Cash Flows (${cashFlowsLoaded ? cashFlows.length : '—'})`} />
          <Tab label="Performance" />
          <Tab label="Covenants" />
        </Tabs>

        {tab === 0 && (
          <Box sx={{ p: 2 }}>
            <Button variant="contained" onClick={() => navigate('/properties/new')} sx={{ mb: 2 }}>
              Add Property
            </Button>
            {properties.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No properties recorded yet.
              </Typography>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {properties.map((property) => {
                  const propertyFlowEntry = propertyFlowState[property.id] || {}
                  const flowsForProperty = propertyFlowEntry.data || []
                  const propertyFlowsLoading = propertyFlowEntry.loading
                  const propertyFlowsError = propertyFlowEntry.error
                  const manualState = getManualState(property.id)
                  const manualRows = manualState.rows
                  const hasActiveLoan = Boolean(getPropertyFieldValue(property.id, 'has_active_loan'))
                  const manualEncumbrance = Boolean(
                    getPropertyFieldValue(property.id, 'encumbrance_override')
                  )
                  const computedEncumbrance = hasActiveLoan || manualEncumbrance
                  return (
                    <Accordion
                      key={property.id}
                      disableGutters
                      onChange={handlePropertyAccordionChange(property.id, property)}
                    >
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Box
                          sx={{
                            width: '100%',
                            display: 'flex',
                            justifyContent: 'space-between',
                            flexWrap: 'wrap',
                            gap: 2,
                            alignItems: 'center'
                          }}
                        >
                          <Box>
                            <Typography variant="subtitle1">
                              {property.property_name || property.property_id || `Property #${property.id}`}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              {property.property_type || 'Type N/A'} · {property.city || 'City N/A'}, {property.state || 'State N/A'}
                            </Typography>
                            {property.is_encumbered && (
                              <Typography variant="caption" color="error">
                                Encumbered
                              </Typography>
                            )}
                          </Box>
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <Button
                              size="small"
                              color="error"
                              onClick={() => handleDeleteProperty(property.id)}
                            >
                              Delete
                            </Button>
                          </Box>
                        </Box>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Box sx={{ mb: 3 }}>
                          <Typography variant="subtitle2" sx={{ mb: 1 }}>
                            Property Details
                          </Typography>
                          <Grid container spacing={2}>
                            <Grid item xs={12} sm={6} md={3}>
                              <TextField
                                fullWidth
                                size="small"
                                label="Property Name"
                                required
                                value={getPropertyFieldValue(property.id, 'property_name')}
                                onChange={(e) =>
                                  handlePropertyFieldChange(property.id, 'property_name', e.target.value)
                                }
                              />
                            </Grid>
                            <Grid item xs={12} sm={6} md={3}>
                              <TextField
                                fullWidth
                                size="small"
                                label="Property ID"
                                required
                                value={getPropertyFieldValue(property.id, 'property_id')}
                                onChange={(e) =>
                                  handlePropertyFieldChange(property.id, 'property_id', e.target.value)
                                }
                              />
                            </Grid>
                            <Grid item xs={12} sm={6} md={3}>
                              <TextField
                                fullWidth
                                size="small"
                                label="Property Type"
                                value={getPropertyFieldValue(property.id, 'property_type')}
                                onChange={(e) =>
                                  handlePropertyFieldChange(property.id, 'property_type', e.target.value)
                                }
                              />
                            </Grid>
                            <Grid item xs={12} sm={6} md={3}>
                              <TextField
                                fullWidth
                                size="small"
                                label="Ownership %"
                                type="text"
                                inputMode="numeric"
                                helperText="Decimal (1 = 100%)"
                                value={getPropertyFieldValue(property.id, 'ownership_percent')}
                                onChange={(e) =>
                                  handlePropertyFieldChange(property.id, 'ownership_percent', e.target.value)
                                }
                                inputProps={{ step: 0.01, min: 0, max: 1 }}
                              />
                            </Grid>
                            <Grid item xs={12}>
                              <TextField
                                fullWidth
                                size="small"
                                label="Address"
                                value={getPropertyFieldValue(property.id, 'address')}
                                onChange={(e) =>
                                  handlePropertyFieldChange(property.id, 'address', e.target.value)
                                }
                              />
                            </Grid>
                            <Grid item xs={12} sm={4}>
                              <TextField
                                fullWidth
                                size="small"
                                label="City"
                                value={getPropertyFieldValue(property.id, 'city')}
                                onChange={(e) =>
                                  handlePropertyFieldChange(property.id, 'city', e.target.value)
                                }
                              />
                            </Grid>
                            <Grid item xs={12} sm={4}>
                              <TextField
                                fullWidth
                                size="small"
                                label="State"
                                value={getPropertyFieldValue(property.id, 'state')}
                                onChange={(e) =>
                                  handlePropertyFieldChange(property.id, 'state', e.target.value)
                                }
                              />
                            </Grid>
                            <Grid item xs={12} sm={4}>
                              <TextField
                                fullWidth
                                size="small"
                                label="Zip Code"
                                value={getPropertyFieldValue(property.id, 'zip_code')}
                                onChange={(e) =>
                                  handlePropertyFieldChange(property.id, 'zip_code', e.target.value)
                                }
                              />
                            </Grid>
                            <Grid item xs={12} sm={6} md={3}>
                              <TextField
                                fullWidth
                                size="small"
                                label="Purchase Price"
                                type="text"
                                inputMode="numeric"
                                value={getPropertyCurrencyValue(property.id, 'purchase_price')}
                                onChange={(e) =>
                                  handlePropertyFieldChange(property.id, 'purchase_price', e.target.value)
                                }
                                onFocus={() => setFocusedPropertyCurrencyField(`${property.id}:purchase_price`)}
                                onBlur={() =>
                                  setFocusedPropertyCurrencyField((prev) =>
                                    prev === `${property.id}:purchase_price` ? null : prev
                                  )
                                }
                              />
                            </Grid>
                            <Grid item xs={12} sm={6} md={3}>
                              <TextField
                                fullWidth
                                size="small"
                                label="Market Value (Analysis Start)"
                                type="text"
                                inputMode="numeric"
                                required
                                value={getPropertyCurrencyValue(property.id, 'market_value_start')}
                                onChange={(e) =>
                                  handlePropertyFieldChange(property.id, 'market_value_start', e.target.value)
                                }
                                onFocus={() =>
                                  setFocusedPropertyCurrencyField(`${property.id}:market_value_start`)
                                }
                                onBlur={() =>
                                  setFocusedPropertyCurrencyField((prev) =>
                                    prev === `${property.id}:market_value_start` ? null : prev
                                  )
                                }
                              />
                            </Grid>
                            <Grid item xs={12} sm={6} md={3}>
                              <TextField
                                fullWidth
                                size="small"
                                label="Initial NOI"
                                type="text"
                                inputMode="numeric"
                                value={getPropertyCurrencyValue(property.id, 'initial_noi')}
                                onChange={(e) =>
                                  handlePropertyFieldChange(property.id, 'initial_noi', e.target.value)
                                }
                                onFocus={() => setFocusedPropertyCurrencyField(`${property.id}:initial_noi`)}
                                onBlur={() =>
                                  setFocusedPropertyCurrencyField((prev) =>
                                    prev === `${property.id}:initial_noi` ? null : prev
                                  )
                                }
                              />
                            </Grid>
                            <Grid item xs={12} sm={6} md={3}>
                              <TextField
                                fullWidth
                                size="small"
                                label="Building Size (sq ft)"
                                type="number"
                                value={getPropertyFieldValue(property.id, 'building_size')}
                                onChange={(e) =>
                                  handlePropertyFieldChange(property.id, 'building_size', e.target.value)
                                }
                              />
                            </Grid>
                            <Grid item xs={12} sm={6} md={3}>
                              <TextField
                                fullWidth
                                size="small"
                                label="Purchase Date"
                                type="date"
                                value={getPropertyFieldValue(property.id, 'purchase_date')}
                                onChange={(e) =>
                                  handlePropertyFieldChange(property.id, 'purchase_date', e.target.value)
                                }
                                InputLabelProps={{ shrink: true }}
                              />
                            </Grid>
                            <Grid item xs={12} sm={6} md={3}>
                              <TextField
                                fullWidth
                                size="small"
                                label="Exit Date"
                                type="date"
                                value={getPropertyFieldValue(property.id, 'exit_date')}
                                onChange={(e) =>
                                  handlePropertyFieldChange(property.id, 'exit_date', e.target.value)
                                }
                                InputLabelProps={{ shrink: true }}
                              />
                            </Grid>
                            <Grid item xs={12} sm={6} md={3}>
                              <TextField
                                fullWidth
                                size="small"
                                label="NOI Growth Rate"
                                type="number"
                                inputProps={{ step: 0.01 }}
                                value={getPropertyFieldValue(property.id, 'noi_growth_rate')}
                                onChange={(e) =>
                                  handlePropertyFieldChange(property.id, 'noi_growth_rate', e.target.value)
                                }
                              />
                            </Grid>
                            <Grid item xs={12} sm={6} md={3}>
                              <TextField
                                fullWidth
                                size="small"
                                label="Exit Cap Rate"
                                type="number"
                                inputProps={{ step: 0.01 }}
                                value={getPropertyFieldValue(property.id, 'exit_cap_rate')}
                                onChange={(e) =>
                                  handlePropertyFieldChange(property.id, 'exit_cap_rate', e.target.value)
                                }
                                required
                              />
                            </Grid>
                            <Grid item xs={12} sm={6} md={3}>
                              <TextField
                                fullWidth
                                size="small"
                                label="Disposition Price Override"
                                type="text"
                                inputMode="numeric"
                                value={getPropertyCurrencyValue(property.id, 'disposition_price_override')}
                                onChange={(e) =>
                                  handlePropertyFieldChange(
                                    property.id,
                                    'disposition_price_override',
                                    e.target.value
                                  )
                                }
                                onFocus={() =>
                                  setFocusedPropertyCurrencyField(`${property.id}:disposition_price_override`)
                                }
                                onBlur={() =>
                                  setFocusedPropertyCurrencyField((prev) =>
                                    prev === `${property.id}:disposition_price_override` ? null : prev
                                  )
                                }
                                helperText="Leave blank to use NOI/exit cap calculation"
                              />
                            </Grid>
                            <Grid item xs={12} sm={6} md={3}>
                              <TextField
                                fullWidth
                                size="small"
                                label="Capex % of NOI"
                                type="number"
                                inputProps={{ step: 0.01, min: 0 }}
                                helperText="Decimal percent (0.1 = 10%)"
                                value={getPropertyFieldValue(property.id, 'capex_percent_of_noi')}
                                onChange={(e) =>
                                  handlePropertyFieldChange(property.id, 'capex_percent_of_noi', e.target.value)
                                }
                              />
                            </Grid>
                            <Grid item xs={12} sm={6} md={3}>
                              <TextField
                                fullWidth
                                size="small"
                                label="Year 1 Cap Rate (Calculated)"
                                value={
                                  getPropertyFieldValue(property.id, 'calculated_year1_cap_rate') ||
                                  getPropertyFieldValue(property.id, 'year_1_cap_rate')
                                }
                                InputProps={{ readOnly: true }}
                                helperText="Calculated after saving"
                              />
                            </Grid>
                            <Grid item xs={12} md={6}>
                              <Box
                                sx={{
                                  border: '1px solid',
                                  borderColor: 'divider',
                                  borderRadius: 1,
                                  p: 2
                                }}
                              >
                                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                                  Encumbrance
                                </Typography>
                                <FormControlLabel
                                  control={<Checkbox checked={computedEncumbrance} disabled />}
                                  label={
                                    hasActiveLoan
                                      ? 'Encumbered (active loan)'
                                      : manualEncumbrance
                                      ? 'Encumbered (manual override)'
                                      : 'Unencumbered'
                                  }
                                />
                                <FormControlLabel
                                  control={
                                    <Checkbox
                                      checked={manualEncumbrance}
                                      onChange={(e) =>
                                        handlePropertyEncumbranceOverrideChange(
                                          property.id,
                                          e.target.checked
                                        )
                                      }
                                      disabled={hasActiveLoan}
                                    />
                                  }
                                  label="Manually mark as encumbered"
                                />
                                {hasActiveLoan && (
                                  <Typography variant="body2" color="text.secondary" sx={{ mb: manualEncumbrance ? 1 : 0 }}>
                                    Active debt automatically marks this property as encumbered.
                                  </Typography>
                                )}
                                {manualEncumbrance && (
                                  <TextField
                                    fullWidth
                                    size="small"
                                    label="Encumbrance Note"
                                    value={getPropertyFieldValue(property.id, 'encumbrance_note')}
                                    onChange={(e) =>
                                      handlePropertyFieldChange(
                                        property.id,
                                        'encumbrance_note',
                                        e.target.value
                                      )
                                    }
                                    helperText="Explain non-debt encumbrance"
                                  />
                                )}
                              </Box>
                            </Grid>
                          </Grid>
                          <Box sx={{ mt: 2 }}>
                            {propertyFormStatus[property.id]?.error && (
                              <Typography variant="body2" color="error" sx={{ mb: 1 }}>
                                {propertyFormStatus[property.id].error}
                              </Typography>
                            )}
                            {propertyFormStatus[property.id]?.success && (
                              <Typography variant="body2" color="success.main" sx={{ mb: 1 }}>
                                {propertyFormStatus[property.id].success}
                              </Typography>
                            )}
                            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                              <Button
                                size="small"
                                onClick={() => handlePropertyFormReset(property.id)}
                                disabled={propertyFormStatus[property.id]?.saving}
                              >
                                Reset
                              </Button>
                              <Button
                                size="small"
                                variant="contained"
                                onClick={() => handleSaveProperty(property.id)}
                                disabled={propertyFormStatus[property.id]?.saving}
                              >
                                {propertyFormStatus[property.id]?.saving ? 'Saving…' : 'Save Property'}
                              </Button>
                            </Box>
                          </Box>
                        </Box>

                        <Divider sx={{ my: 2 }} />

                        <Box
                          sx={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            mb: 1
                          }}
                        >
                          <Typography variant="subtitle2">Cash Flows</Typography>
                          <Button
                            size="small"
                            onClick={() => togglePropertyCashFlowSection(property.id)}
                          >
                            {isPropertyCashFlowOpen(property.id) ? 'Hide' : 'Show'}
                          </Button>
                        </Box>
                        <Collapse in={isPropertyCashFlowOpen(property.id)} timeout="auto" unmountOnExit>
                          {propertyFlowsLoading ? (
                            <Typography variant="body2" color="text.secondary">
                              Loading cash flows...
                            </Typography>
                          ) : propertyFlowsError ? (
                            <Typography variant="body2" color="error">
                              {propertyFlowsError}
                            </Typography>
                          ) : flowsForProperty.length === 0 ? (
                            <Typography variant="body2" color="text.secondary">
                              No cash flows yet for this property.
                            </Typography>
                          ) : (
                            <TableContainer>
                              <Table size="small">
                                <TableHead>
                                  <TableRow>
                                    <TableCell>Date</TableCell>
                                    <TableCell>Type</TableCell>
                                    <TableCell align="right">Amount</TableCell>
                                    <TableCell>Description</TableCell>
                                  </TableRow>
                                </TableHead>
                                <TableBody>
                                  {flowsForProperty.map((cf) => (
                                    <TableRow key={`${property.id}-${cf.id || cf.date}-${cf.cash_flow_type}`}>
                                      <TableCell>{cf.date}</TableCell>
                                      <TableCell>{cf.cash_flow_type || 'Uncategorized'}</TableCell>
                                      <TableCell align="right">{formatCurrency(cf.amount)}</TableCell>
                                      <TableCell>{cf.description || '—'}</TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </TableContainer>
                          )}
                        </Collapse>

                        <Divider sx={{ my: 2 }} />

                        {property.monthly_market_values && property.monthly_market_values.length > 0 && (
                          <Box sx={{ mb: 2 }}>
                            <Typography variant="subtitle2" sx={{ mb: 1 }}>
                              Market Value Projection
                            </Typography>
                            <TableContainer sx={{ maxHeight: 260 }}>
                              <Table size="small" stickyHeader>
                                <TableHead>
                                  <TableRow>
                                    <TableCell>Date</TableCell>
                                    <TableCell align="right">Forward NOI (12m)</TableCell>
                                    <TableCell align="right">Cap Rate</TableCell>
                                    <TableCell align="right">Market Value</TableCell>
                                  </TableRow>
                                </TableHead>
                                <TableBody>
                                  {property.monthly_market_values.map((mv) => (
                                    <TableRow key={`${property.id}-${mv.date}`}>
                                      <TableCell>{mv.date}</TableCell>
                                      <TableCell align="right">{formatCurrency(mv.forward_noi_12m)}</TableCell>
                                      <TableCell align="right">{formatPercent(mv.cap_rate)}</TableCell>
                                      <TableCell align="right">{formatCurrency(mv.market_value)}</TableCell>
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </TableContainer>
                          </Box>
                        )}

                        <Box sx={{ mb: 2 }}>
                          <Typography variant="subtitle2" sx={{ mb: 1 }}>
                            Manual NOI & Capex
                          </Typography>
                          <FormControlLabel
                            control={
                              <Switch
                                checked={!!property.use_manual_noi_capex}
                                onChange={(e) => handleManualToggle(property.id, e.target.checked)}
                              />
                            }
                            label="Use manual entries"
                          />
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            Enter annual totals or specify monthly overrides to replace projected NOI and Capex.
                          </Typography>

                          {manualState.error && (
                            <Alert severity="error" sx={{ mb: 1 }}>
                              {manualState.error}
                              <Button
                                size="small"
                                sx={{ ml: 2 }}
                                onClick={() => loadManualCashFlows(property.id)}
                                disabled={manualState.loading}
                              >
                                Retry
                              </Button>
                            </Alert>
                          )}

                          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1 }}>
                            <Button
                              size="small"
                              variant="outlined"
                              onClick={() => handleManualPrefillRows(property.id, property)}
                              disabled={manualState.loading}
                            >
                              Prefill Years
                            </Button>
                            <Button
                              size="small"
                              variant="outlined"
                              onClick={() => handleManualAddRow(property.id)}
                              disabled={manualState.loading}
                            >
                              Add Row
                            </Button>
                            <Button
                              size="small"
                              variant="outlined"
                              onClick={() => loadManualCashFlows(property.id)}
                              disabled={manualState.loading}
                            >
                              {manualState.loaded ? 'Reload Entries' : 'Load Entries'}
                            </Button>
                          </Box>

                          {manualState.loading && !manualState.loaded ? (
                            <Typography variant="body2" color="text.secondary">
                              Loading manual entries...
                            </Typography>
                          ) : !manualState.loaded ? (
                            <Typography variant="body2" color="text.secondary">
                              Click "Load Entries" to fetch manual overrides for this property.
                            </Typography>
                          ) : (
                            <>
                              {manualState.loading && manualState.loaded && (
                                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                                  Refreshing entries...
                                </Typography>
                              )}
                              <TableContainer>
                                <Table size="small">
                                  <TableHead>
                                    <TableRow>
                                      <TableCell>Year</TableCell>
                                      <TableCell>Frequency</TableCell>
                                      <TableCell>Month</TableCell>
                                      <TableCell>NOI</TableCell>
                                      <TableCell>Capex</TableCell>
                                      <TableCell align="right">Actions</TableCell>
                                    </TableRow>
                                  </TableHead>
                                  <TableBody>
                                    {manualRows.length === 0 ? (
                                      <TableRow>
                                        <TableCell colSpan={6}>
                                          <Typography variant="body2" color="text.secondary">
                                            No manual entries yet.
                                          </Typography>
                                        </TableCell>
                                      </TableRow>
                                    ) : (
                                      manualRows.map((row, idx) => (
                                        <TableRow key={`${property.id}-manual-${idx}`}>
                                          <TableCell width="12%">
                                            <TextField
                                              size="small"
                                              value={row.year || ''}
                                              onChange={(e) =>
                                                handleManualRowChange(property.id, idx, 'year', e.target.value)
                                              }
                                              placeholder="2026"
                                            />
                                          </TableCell>
                                          <TableCell width="18%">
                                            <TextField
                                              select
                                              size="small"
                                              value={row.frequency || 'annual'}
                                              onChange={(e) =>
                                                handleManualRowChange(property.id, idx, 'frequency', e.target.value)
                                              }
                                            >
                                              <MenuItem value="annual">Annual</MenuItem>
                                              <MenuItem value="monthly">Monthly</MenuItem>
                                            </TextField>
                                          </TableCell>
                                          <TableCell width="15%">
                                            <TextField
                                              select
                                              size="small"
                                              value={row.month || ''}
                                              onChange={(e) =>
                                                handleManualRowChange(property.id, idx, 'month', e.target.value)
                                              }
                                              disabled={(row.frequency || 'annual') !== 'monthly'}
                                            >
                                              {[...Array(12)].map((_, monthIdx) => (
                                                <MenuItem key={monthIdx + 1} value={String(monthIdx + 1)}>
                                                  {monthIdx + 1}
                                                </MenuItem>
                                              ))}
                                            </TextField>
                                          </TableCell>
                                          <TableCell width="22%">
                                            <TextField
                                              size="small"
                                              value={displayManualValue(
                                                property.id,
                                                idx,
                                                'annual_noi',
                                                row.annual_noi
                                              )}
                                              onFocus={() =>
                                                handleManualFieldFocus(property.id, idx, 'annual_noi')
                                              }
                                              onBlur={() =>
                                                handleManualFieldBlur(property.id, idx, 'annual_noi')
                                              }
                                              onChange={(e) =>
                                                handleManualRowChange(
                                                  property.id,
                                                  idx,
                                                  'annual_noi',
                                                  e.target.value
                                                )
                                              }
                                              inputMode="numeric"
                                              placeholder="1,000,000"
                                            />
                                          </TableCell>
                                          <TableCell width="22%">
                                            <TextField
                                              size="small"
                                              value={displayManualValue(
                                                property.id,
                                                idx,
                                                'annual_capex',
                                                row.annual_capex
                                              )}
                                              onFocus={() =>
                                                handleManualFieldFocus(property.id, idx, 'annual_capex')
                                              }
                                              onBlur={() =>
                                                handleManualFieldBlur(property.id, idx, 'annual_capex')
                                              }
                                              onChange={(e) =>
                                                handleManualRowChange(
                                                  property.id,
                                                  idx,
                                                  'annual_capex',
                                                  e.target.value
                                                )
                                              }
                                              inputMode="numeric"
                                              placeholder="100,000"
                                            />
                                          </TableCell>
                                          <TableCell align="right" width="11%">
                                            <Button
                                              size="small"
                                              color="error"
                                              onClick={() => handleManualRemoveRow(property.id, idx)}
                                              disabled={manualState.loading}
                                            >
                                              Remove
                                            </Button>
                                          </TableCell>
                                        </TableRow>
                                      ))
                                    )}
                                  </TableBody>
                                </Table>
                              </TableContainer>
                              <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 1 }}>
                                <Button
                                  size="small"
                                  variant="contained"
                                  onClick={() => handleManualSave(property.id, property)}
                                  disabled={manualState.loading}
                                >
                                  Save Manual Entries
                                </Button>
                              </Box>
                            </>
                          )}
                        </Box>

                        <Divider sx={{ my: 2 }} />

                        <Typography variant="subtitle2" sx={{ mb: 1 }}>
                          Ownership History
                        </Typography>
                        {ownershipEvents[property.id]?.error && (
                          <Alert
                            severity="error"
                            sx={{ mb: 1 }}
                            onClose={() =>
                              setOwnershipEvents((prev) => ({
                                ...prev,
                                [property.id]: { ...prev[property.id], error: '' }
                              }))
                            }
                          >
                            {ownershipEvents[property.id].error}
                          </Alert>
                        )}
                        {ownershipEvents[property.id]?.loading ? (
                          <Typography variant="body2" color="text.secondary">
                            Loading ownership history...
                          </Typography>
                        ) : ownershipEvents[property.id]?.data?.length ? (
                          <TableContainer sx={{ mb: 2 }}>
                            <Table size="small">
                              <TableHead>
                                <TableRow>
                                  <TableCell>Date</TableCell>
                                  <TableCell align="right">Ownership %</TableCell>
                                  <TableCell>Note</TableCell>
                                  <TableCell align="right">Actions</TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {ownershipEvents[property.id].data.map((event) => (
                                  <TableRow key={`ownership-${event.id}`}>
                                    <TableCell>{event.event_date}</TableCell>
                                    <TableCell align="right">{formatPercent(event.ownership_percent)}</TableCell>
                                    <TableCell>{event.note || '—'}</TableCell>
                                    <TableCell align="right">
                                      <Button
                                        size="small"
                                        color="error"
                                        onClick={() => handleDeleteOwnershipEvent(property.id, event.id)}
                                      >
                                        Delete
                                      </Button>
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </TableContainer>
                        ) : (
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                            No ownership events recorded yet.
                          </Typography>
                        )}

                        <Grid container spacing={2}>
                          <Grid item xs={12} sm={4}>
                            <TextField
                              fullWidth
                              size="small"
                              label="Event Date"
                              type="date"
                              value={ownershipEventForms[property.id]?.event_date || ''}
                              onChange={(e) =>
                                handleOwnershipFormChange(property.id, 'event_date', e.target.value)
                              }
                              InputLabelProps={{ shrink: true }}
                            />
                          </Grid>
                          <Grid item xs={12} sm={4}>
                            <TextField
                              fullWidth
                              size="small"
                              label="Ownership %"
                              type="number"
                              value={ownershipEventForms[property.id]?.ownership_percent ?? ''}
                              onChange={(e) =>
                                handleOwnershipFormChange(property.id, 'ownership_percent', e.target.value)
                              }
                              inputProps={{ step: 0.01, min: 0, max: 1 }}
                              helperText="Decimal (e.g., 1 = 100%)"
                            />
                          </Grid>
                          <Grid item xs={12} sm={4}>
                            <TextField
                              fullWidth
                              size="small"
                              label="Note"
                              value={ownershipEventForms[property.id]?.note || ''}
                              onChange={(e) =>
                                handleOwnershipFormChange(property.id, 'note', e.target.value)
                              }
                            />
                          </Grid>
                          <Grid item xs={12}>
                            <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                              <Button
                                variant="outlined"
                                size="small"
                                onClick={() => handleAddOwnershipEvent(property.id)}
                              >
                                Add Ownership Event
                              </Button>
                            </Box>
                          </Grid>
                        </Grid>
                      </AccordionDetails>
                    </Accordion>
                  )
                })}
              </Box>
            )}
          </Box>
        )}

        {tab === 1 && (
          <Box sx={{ p: 2 }}>
            <Button variant="contained" onClick={() => navigate('/loans/new')} sx={{ mb: 2 }}>
              Add Loan
            </Button>
            {loans.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No loans recorded yet.
              </Typography>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {loans.map((loan) => {
                  const propertyForLoan = propertyMap.get(loan.property_id)
                  const loanFlowEntry = loanFlowState[loan.id] || {
                    data: [],
                    loading: false,
                    error: ''
                  }
                  const flowsForLoan = loanFlowEntry.data || []
                  const sortedLoanFlows = sortLoanFlows(flowsForLoan)
                  return (
                    <Accordion
                      key={loan.id}
                      disableGutters
                      onChange={handleLoanAccordionChange(loan.id)}
                      expanded={loanAccordionExpanded[loan.id] ?? false}
                    >
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Box
                          sx={{
                            width: '100%',
                            display: 'flex',
                            justifyContent: 'space-between',
                            flexWrap: 'wrap',
                            gap: 2,
                            alignItems: 'center'
                          }}
                        >
                          <Box>
                            <Typography variant="subtitle1">
                              {loan.loan_name || loan.loan_id || `Loan #${loan.id}`}
                              {propertyForLoan ? ` · ${propertyForLoan.property_name || propertyForLoan.property_id || ''}` : ''}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Principal {formatCurrency(loan.principal_amount)} · Rate {formatLoanRateLabel(loan)}
                            </Typography>
                          </Box>
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            <Button size="small" onClick={() => navigate(`/loans/${loan.id}/edit`)}>
                              Edit
                            </Button>
                            <Button
                              size="small"
                              color="error"
                              onClick={() => handleDeleteLoan(loan.id)}
                            >
                              Delete
                            </Button>
                          </Box>
                        </Box>
                      </AccordionSummary>
                      <AccordionDetails>
                        <Grid container spacing={2} sx={{ mb: 2 }}>
                          <Grid item xs={12} sm={6} md={3}>
                            <Typography variant="subtitle2" color="text.secondary">
                              Property
                            </Typography>
                            <Typography>
                              {propertyForLoan
                                ? propertyForLoan.property_name || propertyForLoan.property_id
                                : '—'}
                            </Typography>
                          </Grid>
                          <Grid item xs={12} sm={6} md={3}>
                            <Typography variant="subtitle2" color="text.secondary">
                              Origination
                            </Typography>
                            <Typography>{loan.origination_date || '—'}</Typography>
                          </Grid>
                          <Grid item xs={12} sm={6} md={3}>
                            <Typography variant="subtitle2" color="text.secondary">
                              Maturity
                            </Typography>
                            <Typography>{loan.maturity_date || '—'}</Typography>
                          </Grid>
                          <Grid item xs={12} sm={6} md={3}>
                            <Typography variant="subtitle2" color="text.secondary">
                              Payment Frequency
                            </Typography>
                            <Typography>{loan.payment_frequency || 'monthly'}</Typography>
                          </Grid>
                        </Grid>

                        <Divider sx={{ my: 2 }} />

                        <Typography variant="subtitle2" sx={{ mb: 1 }}>
                          Cash Flows
                        </Typography>
                        {loanFlowEntry.loading && flowsForLoan.length === 0 ? (
                          <Typography variant="body2" color="text.secondary">
                            Loading cash flows...
                          </Typography>
                        ) : loanFlowEntry.error ? (
                          <Typography variant="body2" color="error">
                            {loanFlowEntry.error}
                          </Typography>
                        ) : flowsForLoan.length === 0 ? (
                          <Typography variant="body2" color="text.secondary">
                            No cash flows yet for this loan.
                          </Typography>
                        ) : (
                          <TableContainer>
                            <Table size="small">
                              <TableHead>
                                <TableRow>
                                  <TableCell>Date</TableCell>
                                  <TableCell>Type</TableCell>
                                  <TableCell align="right">SOFR Rate</TableCell>
                                  <TableCell align="right">Amount</TableCell>
                                  <TableCell>Description</TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {sortedLoanFlows.map((cf) => (
                                  <TableRow key={`${loan.id}-${cf.id || cf.date}-${cf.cash_flow_type}`}>
                                    <TableCell>{cf.date}</TableCell>
                                    <TableCell>{cf.cash_flow_type || 'Uncategorized'}</TableCell>
                                    <TableCell align="right">{renderFloatingRate(cf)}</TableCell>
                                    <TableCell align="right">{formatCurrency(cf.amount)}</TableCell>
                                    <TableCell>{cf.description || '—'}</TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </TableContainer>
                        )}
                      </AccordionDetails>
                    </Accordion>
                  )
                })}
              </Box>
            )}
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
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {preferredEquities.map((pe) => (
                    <TableRow key={pe.id}>
                      <TableCell>{pe.name}</TableCell>
                      <TableCell>{formatCurrency(pe.initial_investment)}</TableCell>
                      <TableCell>
                        {pe.preferred_return != null ? `${(pe.preferred_return * 100).toFixed(2)}%` : '—'}
                      </TableCell>
                      <TableCell>{pe.investment_date}</TableCell>
                      <TableCell>
                        <Button
                          size="small"
                          color="error"
                          onClick={() => handleDeletePreferredEquity(pe.id)}
                        >
                          Delete
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}

        {tab === 3 && (
          <Box sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2, gap: 1, flexWrap: 'wrap' }}>
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                onClick={handleDownloadCashFlowReport}
                disabled={downloadingReport}
              >
                {downloadingReport ? 'Preparing…' : 'Download Excel'}
              </Button>
            </Box>
            <Paper sx={{ p: 2, mb: 3 }} variant="outlined">
              <Typography variant="subtitle1" sx={{ mb: 1 }}>
                Add Fund-Level Cash Flow
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Capital Calls are cash inflows. Distributions and Redemption Payments are cash outflows.
              </Typography>
              <Box component="form" onSubmit={handleManualFlowSubmit}>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={3}>
                    <TextField
                      fullWidth
                      label="Date"
                      type="date"
                      value={manualFlowForm.date}
                      onChange={(e) => handleManualFlowFieldChange('date', e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      size="small"
                      required
                    />
                  </Grid>
                      <Grid item xs={12} sm={3}>
                        <TextField
                          fullWidth
                          label="Amount"
                          type="text"
                          inputMode="numeric"
                          value={manualFlowForm.amount}
                          onChange={handleManualFlowInputChange}
                          onBlur={handleManualFlowAmountBlur}
                          size="small"
                          inputProps={{ step: 0.01 }}
                          required
                        />
                      </Grid>
                      <Grid item xs={12} sm={3}>
                        <TextField
                          fullWidth
                          select
                          label="Type"
                          value={manualFlowForm.type}
                          onChange={(e) => handleManualFlowFieldChange('type', e.target.value)}
                          size="small"
                    >
                      {manualFlowOptions.map((option) => (
                        <MenuItem key={option.value} value={option.value}>
                          {option.label}
                        </MenuItem>
                      ))}
                    </TextField>
                  </Grid>
                      <Grid item xs={12} sm={3}>
                        <TextField
                          fullWidth
                          label="Description"
                          value={manualFlowForm.description}
                          onChange={(e) => handleManualFlowFieldChange('description', e.target.value)}
                          size="small"
                        />
                  </Grid>
                  <Grid item xs={12} sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <Button type="submit" variant="contained">
                      Save Cash Flow
                    </Button>
                  </Grid>
                </Grid>
              </Box>
            </Paper>
            {cashFlowsLoading && !cashFlowsLoaded ? (
              <Typography variant="body2" color="text.secondary">
                Loading portfolio cash flows...
              </Typography>
            ) : aggregatedByDate.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No cash flows recorded yet.
              </Typography>
            ) : (
              <>
                <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={applyOwnership}
                        onChange={(e) => setApplyOwnership(e.target.checked)}
                      />
                    }
                    label="Apply ownership share"
                  />
                </Box>
                <TableContainer
                  sx={{
                    maxHeight: '70vh',
                    position: 'relative',
                    borderRadius: 3,
                    border: '1px solid rgba(15,23,42,0.08)'
                  }}
                >
                  <Table
                    size="small"
                    stickyHeader
                    sx={{
                      '& .MuiTableCell-stickyHeader': {
                        backgroundColor: 'background.paper',
                        zIndex: 2
                      }
                    }}
                  >
                  <TableHead>
                    <TableRow>
                      <TableCell />
                      <TableCell>Date</TableCell>
                      <TableCell align="right">Beginning Cash</TableCell>
                      <TableCell align="right">Total</TableCell>
                      <TableCell align="right">Ending Cash</TableCell>
                      <TableCell align="right">Market Value (Current)</TableCell>
                      <TableCell align="right">Market Value (Prior)</TableCell>
                      <TableCell align="right">Appreciation</TableCell>
                      {cashFlowTypes.map((type) => (
                        <TableCell align="right" key={`portfolio-type-${type}`}>
                          {type}
                        </TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {aggregatedByDate.map((entry) => {
                      const dateKey = entry.date
                      const open = !!dateExpanded[dateKey]

                      return (
                        <React.Fragment key={dateKey}>
                          <TableRow>
                            <TableCell>
                              <IconButton size="small" onClick={() => toggleDateRow(dateKey)}>
                                {open ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
                              </IconButton>
                            </TableCell>
                            <TableCell>{dateKey}</TableCell>
                            <TableCell align="right">{formatCurrency(entry.beginning_cash)}</TableCell>
                            <TableCell align="right">{formatCurrency(entry.total)}</TableCell>
                            <TableCell align="right">{formatCurrency(entry.ending_cash)}</TableCell>
                            <TableCell align="right">{formatCurrency(entry.market_value_current)}</TableCell>
                            <TableCell align="right">{formatCurrency(entry.market_value_prior)}</TableCell>
                            <TableCell align="right">{formatCurrency(entry.appreciation_total)}</TableCell>
                            {cashFlowTypes.map((type) => (
                              <TableCell align="right" key={`${dateKey}-${type}`}>
                                {formatCurrency(entry.typeTotals[type] || 0)}
                              </TableCell>
                            ))}
                          </TableRow>
                          <TableRow>
                            <TableCell
                              colSpan={8 + cashFlowTypes.length}
                              sx={{ py: 0, border: 0 }}
                            >
                              <Collapse in={open} timeout="auto" unmountOnExit>
                                <Box sx={{ m: 2 }}>
                                  {entry.properties.length === 0 ? (
                                    <Typography variant="body2" color="text.secondary">
                                      No property allocations for this date.
                                    </Typography>
                                  ) : (
                                    <Table size="small">
                                      <TableHead>
                                        <TableRow>
                                          <TableCell />
                                          <TableCell>Property</TableCell>
                                          <TableCell align="right">Total</TableCell>
                                          <TableCell align="right">Market Value (Current)</TableCell>
                                          <TableCell align="right">Market Value (Prior)</TableCell>
                                          <TableCell align="right">Appreciation</TableCell>
                                          {cashFlowTypes.map((type) => (
                                            <TableCell align="right" key={`property-header-${type}`}>
                                              {type}
                                            </TableCell>
                                          ))}
                                        </TableRow>
                                      </TableHead>
                                      <TableBody>
                                        {entry.properties.map((propertyEntry) => {
                                          const propertyKey = `${dateKey}|${propertyEntry.propertyId ?? 'unassigned'}`
                                          const propOpen = !!propertyExpanded[propertyKey]
                                          const propertyRecord = propertyMap.get(propertyEntry.propertyId)
                                          const label =
                                            propertyRecord?.property_name ||
                                            propertyRecord?.property_id ||
                                            (propertyEntry.propertyId
                                              ? `Property #${propertyEntry.propertyId}`
                                              : 'Unassigned')

                                          return (
                                            <React.Fragment key={propertyKey}>
                                              <TableRow>
                                                <TableCell>
                                                  <IconButton
                                                    size="small"
                                                    onClick={() => togglePropertyRow(propertyKey)}
                                                  >
                                                    {propOpen ? (
                                                      <KeyboardArrowUpIcon />
                                                    ) : (
                                                      <KeyboardArrowDownIcon />
                                                    )}
                                                  </IconButton>
                                                </TableCell>
                                                <TableCell>
                                                  <Box sx={{ display: 'flex', flexDirection: 'column' }}>
                                                    <Typography variant="body2">{label}</Typography>
                                                    <Typography
                                                      variant="caption"
                                                      color={
                                                        propertyEntry.encumberedOnDate
                                                          ? 'error.main'
                                                          : 'text.secondary'
                                                      }
                                                    >
                                                      {propertyEntry.encumberedOnDate
                                                        ? 'Encumbered'
                                                        : 'Unencumbered'}
                                                    </Typography>
                                                  </Box>
                                                </TableCell>
                                                <TableCell align="right">
                                                  {formatCurrency(propertyEntry.total)}
                                                </TableCell>
                                                <TableCell align="right">
                                                  {formatCurrency(propertyEntry.marketValueCurrent)}
                                                </TableCell>
                                                <TableCell align="right">
                                                  {formatCurrency(propertyEntry.marketValuePrior)}
                                                </TableCell>
                                                <TableCell align="right">
                                                  {formatCurrency(propertyEntry.appreciation)}
                                                </TableCell>
                                                {cashFlowTypes.map((type) => (
                                                  <TableCell
                                                    align="right"
                                                    key={`${propertyKey}-${type}`}
                                                  >
                                                    {formatCurrency(propertyEntry.typeTotals[type] || 0)}
                                                  </TableCell>
                                                ))}
                                              </TableRow>
                                              <TableRow>
                                                <TableCell
                                                  colSpan={6 + cashFlowTypes.length}
                                                  sx={{ py: 0, border: 0 }}
                                                >
                                                  <Collapse in={propOpen} timeout="auto" unmountOnExit>
                                                    <Box sx={{ m: 2 }}>
                                                      {propertyEntry.flows.length === 0 ? (
                                                        <Typography
                                                          variant="body2"
                                                          color="text.secondary"
                                                        >
                                                          No detailed cash flows recorded.
                                                        </Typography>
                                                      ) : (
                                                        <Table size="small">
                                                          <TableHead>
                                                            <TableRow>
                                                              <TableCell>Type</TableCell>
                                                              <TableCell align="right">Amount</TableCell>
                                                              <TableCell>Description</TableCell>
                                                              <TableCell align="right">Loan</TableCell>
                                                            </TableRow>
                                                          </TableHead>
                                                          <TableBody>
                                                            {propertyEntry.flows.map((flow) => {
                                                              const loanForFlow =
                                                                flow.loan_id != null
                                                                  ? loanMap.get(flow.loan_id)
                                                                  : null
                                                              const flowLabel =
                                                                flow.cash_flow_type || 'Uncategorized'
                                                              const loanLabel = loanForFlow
                                                                ? loanForFlow.loan_name ||
                                                                  loanForFlow.loan_id ||
                                                                  `Loan #${loanForFlow.id}`
                                                                : flow.loan_id
                                                                ? `Loan #${flow.loan_id}`
                                                                : '—'

                                                              return (
                                                                <TableRow
                                                                  key={`${propertyKey}-${flow.id || `${flowLabel}-${flow.amount}`}`}
                                                                >
                                                                  <TableCell>{flowLabel}</TableCell>
                                                                  <TableCell align="right">
                                                                    {formatCurrency(
                                                                      applyOwnership
                                                                        ? flow.adjusted_amount
                                                                        : flow.amount
                                                                    )}
                                                                  </TableCell>
                                                                  <TableCell>
                                                                    {flow.description || '—'}
                                                                  </TableCell>
                                                                  <TableCell align="right">
                                                                    {loanLabel}
                                                                  </TableCell>
                                                                </TableRow>
                                                              )
                                                            })}
                                                          </TableBody>
                                                        </Table>
                                                      )}
                                                    </Box>
                                                  </Collapse>
                                                </TableCell>
                                              </TableRow>
                                            </React.Fragment>
                                          )
                                        })}
                                      </TableBody>
                                    </Table>
                                  )}
                                </Box>
                              </Collapse>
                            </TableCell>
                          </TableRow>
                        </React.Fragment>
                      )
                    })}
                  </TableBody>
                  </Table>
                </TableContainer>
              </>
            )}
          </Box>
        )}

        {tab === 4 && (
          <Box sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 2 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={performanceOwnership}
                    onChange={handlePerformanceOwnershipToggle}
                  />
                }
                label="Apply ownership share"
              />
              <Button
                variant="outlined"
                onClick={loadPerformance}
                disabled={performanceLoading}
              >
                {performanceLoading
                  ? 'Calculating…'
                  : performanceLoaded
                  ? 'Refresh'
                  : 'Load Performance'}
              </Button>
            </Box>
            {performanceError && (
              <Alert
                severity="error"
                sx={{ mb: 2 }}
                onClose={() => setPerformanceError('')}
              >
                {performanceError}
              </Alert>
            )}
            {performanceLoading && !performanceLoaded ? (
              <Typography variant="body2" color="text.secondary">
                Calculating quarterly performance…
              </Typography>
            ) : (
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle1" sx={{ mb: 1 }}>
                  Quarterly Performance (Time-Weighted Return)
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Denominator = Beginning NAV + Capital Calls - Redemptions. Net income equals NOI minus Interest Expense. Appreciation reflects property-level market value changes net of capex.
                </Typography>
                {performanceLoading && performanceLoaded && (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    Refreshing performance…
                  </Typography>
                )}
                {!performanceData || (performanceData.quarters || []).length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    No performance periods were found within the analysis window.
                  </Typography>
                ) : (
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell />
                          <TableCell>Quarter</TableCell>
                          <TableCell>Quarter End</TableCell>
                          <TableCell align="right">Beginning NAV</TableCell>
                          <TableCell align="right">Capital Calls</TableCell>
                          <TableCell align="right">Redemptions</TableCell>
                          <TableCell align="right">TWR Denominator</TableCell>
                          <TableCell align="right">Net Income</TableCell>
                          <TableCell align="right">Appreciation</TableCell>
                          <TableCell align="right">Total Return</TableCell>
                          <TableCell align="right">Ending NAV</TableCell>
                          <TableCell align="right">Quarterly TWR</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {(performanceData?.quarters || []).map((row) => {
                          const expanded = !!performanceExpanded[row.label]
                          return (
                            <React.Fragment key={`${row.label}-${row.start_date}`}>
                              <TableRow>
                                <TableCell>
                                  <IconButton
                                    size="small"
                                    onClick={() => togglePerformanceRow(row.label)}
                                  >
                                    {expanded ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
                                  </IconButton>
                                </TableCell>
                                <TableCell>{row.label}</TableCell>
                                <TableCell>{formatDisplayDate(row.end_date)}</TableCell>
                                <TableCell align="right">{formatCurrency(row.beginning_nav)}</TableCell>
                                <TableCell align="right">{formatCurrency(row.capital_calls)}</TableCell>
                                <TableCell align="right">{formatCurrency(row.redemptions)}</TableCell>
                                <TableCell align="right">{formatCurrency(row.denominator)}</TableCell>
                                <TableCell align="right">{formatCurrency(row.income)}</TableCell>
                                <TableCell align="right">{formatCurrency(row.appreciation)}</TableCell>
                                <TableCell align="right">{formatCurrency(row.total_return)}</TableCell>
                                <TableCell align="right">{formatCurrency(row.ending_nav)}</TableCell>
                                <TableCell align="right">{formatPercent(row.twr)}</TableCell>
                              </TableRow>
                              <TableRow>
                                <TableCell colSpan={12} sx={{ p: 0, border: 0 }}>
                                  <Collapse in={expanded} timeout="auto" unmountOnExit>
                                    <Box sx={{ m: 2 }}>
                                      <Typography variant="subtitle2" sx={{ mb: 1 }}>
                                        Property Contribution
                                      </Typography>
                                      {!row.property_details || row.property_details.length === 0 ? (
                                        <Typography variant="body2" color="text.secondary">
                                          No property valuation data for this quarter.
                                        </Typography>
                                      ) : (
                                        <Table size="small">
                                          <TableHead>
                                            <TableRow>
                                              <TableCell>Property</TableCell>
                                              <TableCell align="right">Beginning Value</TableCell>
                                              <TableCell align="right">Ending Value</TableCell>
                                              <TableCell align="right">Capex</TableCell>
                                              <TableCell align="right">Appreciation</TableCell>
                                              <TableCell align="right">Net Income</TableCell>
                                              <TableCell align="right">Quarterly TWR</TableCell>
                                            </TableRow>
                                          </TableHead>
                                          <TableBody>
                                            {row.property_details.map((detail) => (
                                              <TableRow key={`${row.label}-${detail.property_id}`}>
                                                <TableCell>{detail.property_name}</TableCell>
                                                <TableCell align="right">
                                                  {formatCurrency(detail.begin_value)}
                                                </TableCell>
                                                <TableCell align="right">
                                                  {formatCurrency(detail.end_value)}
                                                </TableCell>
                                                <TableCell align="right">
                                                  {formatCurrency(detail.capex)}
                                                </TableCell>
                                                <TableCell align="right">
                                                  {formatCurrency(detail.appreciation)}
                                                </TableCell>
                                                <TableCell align="right">
                                                  {formatCurrency(detail.net_income)}
                                                </TableCell>
                                                <TableCell align="right">
                                                  {formatPercent(detail.twr)}
                                                </TableCell>
                                              </TableRow>
                                            ))}
                                          </TableBody>
                                        </Table>
                                      )}
                                    </Box>
                                  </Collapse>
                                </TableCell>
                              </TableRow>
                            </React.Fragment>
                          )
                        })}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}
              </Paper>
            )}
          </Box>
        )}

        {tab === 5 && (
          <Box sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, gap: 2, flexWrap: 'wrap' }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={covenantOwnership}
                    onChange={handleCovenantOwnershipToggle}
                  />
                }
                label="Apply ownership share"
              />
              <Button
                variant="outlined"
                onClick={() => loadCovenants()}
                disabled={covenantLoading}
              >
                {covenantLoading
                  ? 'Calculating…'
                  : covenantLoaded
                  ? 'Refresh'
                  : 'Load Covenants'}
              </Button>
            </Box>
            {covenantError && (
              <Alert severity="error" sx={{ mb: 2 }} onClose={() => setCovenantError('')}>
                {covenantError}
              </Alert>
            )}
            {covenantLoading && !covenantLoaded ? (
              <Typography variant="body2" color="text.secondary">
                Calculating covenant metrics…
              </Typography>
            ) : !covenantData || (covenantData.months || []).length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No covenant data available for this portfolio.
              </Typography>
            ) : (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell />
                      <TableCell>Month</TableCell>
                      <TableCell align="right">Fund DSCR (TTM)</TableCell>
                      <TableCell align="right">Fund LTV</TableCell>
                      <TableCell align="right">Debt Yield</TableCell>
                      <TableCell align="right">TTM NOI</TableCell>
                      <TableCell align="right">TTM Debt Service</TableCell>
                      <TableCell align="right">Outstanding Debt</TableCell>
                      <TableCell align="right">Market Value</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {(covenantData?.months || []).map((monthEntry) => {
                      const expanded = !!covenantExpanded[monthEntry.date]
                      const fund = monthEntry.fund || {}
                      return (
                        <React.Fragment key={monthEntry.date}>
                          <TableRow>
                            <TableCell>
                              <IconButton
                                size="small"
                                onClick={() => toggleCovenantRow(monthEntry.date)}
                              >
                                {expanded ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
                              </IconButton>
                            </TableCell>
                            <TableCell>{monthEntry.date}</TableCell>
                            <TableCell align="right">{formatRatio(fund.dscr)}</TableCell>
                            <TableCell align="right">{formatPercent(fund.ltv)}</TableCell>
                            <TableCell align="right">{formatPercent(fund.debt_yield)}</TableCell>
                            <TableCell align="right">{formatCurrency(fund.ttm_noi)}</TableCell>
                            <TableCell align="right">{formatCurrency(fund.ttm_debt_service)}</TableCell>
                            <TableCell align="right">{formatCurrency(fund.outstanding_debt)}</TableCell>
                            <TableCell align="right">{formatCurrency(fund.market_value)}</TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell colSpan={10} sx={{ p: 0, border: 0 }}>
                              <Collapse in={expanded} timeout="auto" unmountOnExit>
                                <Box sx={{ m: 2 }}>
                                  {monthEntry.properties && monthEntry.properties.length > 0 ? (
                                    <Table size="small">
                                      <TableHead>
                                        <TableRow>
                                          <TableCell>Property</TableCell>
                                          <TableCell align="right">DSCR</TableCell>
                                          <TableCell align="right">LTV</TableCell>
                                          <TableCell align="right">Debt Yield</TableCell>
                                          <TableCell align="right">TTM NOI</TableCell>
                                          <TableCell align="right">TTM Debt Service</TableCell>
                                          <TableCell align="right">Outstanding Debt</TableCell>
                                          <TableCell align="right">Market Value</TableCell>
                                        </TableRow>
                                      </TableHead>
                                      <TableBody>
                                        {monthEntry.properties.map((property) => (
                                          <TableRow key={`${monthEntry.date}-${property.property_id}`}>
                                            <TableCell>{property.property_name}</TableCell>
                                            <TableCell align="right">{formatRatio(property.dscr)}</TableCell>
                                            <TableCell align="right">{formatPercent(property.ltv)}</TableCell>
                                            <TableCell align="right">{formatPercent(property.debt_yield)}</TableCell>
                                            <TableCell align="right">{formatCurrency(property.ttm_noi)}</TableCell>
                                            <TableCell align="right">{formatCurrency(property.ttm_debt_service)}</TableCell>
                                            <TableCell align="right">{formatCurrency(property.outstanding_debt)}</TableCell>
                                            <TableCell align="right">{formatCurrency(property.market_value)}</TableCell>
                                          </TableRow>
                                        ))}
                                      </TableBody>
                                    </Table>
                                  ) : (
                                    <Typography variant="body2" color="text.secondary">
                                      No property-level data for this month.
                                    </Typography>
                                  )}
                                </Box>
                              </Collapse>
                            </TableCell>
                          </TableRow>
                        </React.Fragment>
                      )
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Box>
        )}
      </Paper>
    </Box>
  )
}

export default PortfolioDetail
