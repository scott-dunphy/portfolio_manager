export const parseNumeric = (value) => {
  if (value === '' || value === null || value === undefined) {
    return null
  }
  const numberValue = Number(value)
  if (Number.isNaN(numberValue)) {
    return null
  }
  return numberValue
}

export const roundToDollar = (value) => {
  const numeric = parseNumeric(value)
  if (numeric === null) {
    return null
  }
  return Math.round(numeric)
}

export const formatCurrencyDisplay = (value) => {
  const rounded = roundToDollar(value)
  if (rounded === null) {
    return '—'
  }
  return new Intl.NumberFormat('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(rounded)
}

export const formatCurrencyInputValue = (value) => {
  if (value === '' || value === null || value === undefined) {
    return ''
  }
  const rounded = roundToDollar(value)
  if (rounded === null) {
    return ''
  }
  return new Intl.NumberFormat('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(rounded)
}

export const normalizeCurrencyInput = (raw) => {
  const cleaned = String(raw ?? '').replace(/,/g, '')
  if (cleaned.trim() === '') {
    return ''
  }
  const numeric = Number(cleaned)
  if (Number.isNaN(numeric)) {
    return ''
  }
  return String(Math.round(numeric))
}

export const sanitizeCurrencyInput = (raw) => {
  if (raw === null || raw === undefined) {
    return ''
  }
  const cleaned = String(raw).replace(/,/g, '').replace(/[^0-9-]/g, '')
  return cleaned
}
