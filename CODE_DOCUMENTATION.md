# Portfolio Manager - Code Documentation

## Overview

The Portfolio Manager is a comprehensive Python-based real estate investment portfolio management system. It provides sophisticated tools for modeling, analyzing, and valuating commercial real estate investments, including properties, loans, preferred equity positions, and carried interest (promote) structures.

## System Architecture

The system is built around six core Python classes that work together to model complex real estate investment scenarios:

1. **Portfolio** - Top-level container managing all investments
2. **Property** - Individual real estate assets with cash flow modeling
3. **Loan** - Debt instruments (secured and unsecured) with amortization schedules
4. **LoanValuation** - Mark-to-market valuation of loan positions
5. **PreferredEquity** - Preferred equity investments backed by loans
6. **CarriedInterest** - Waterfall distribution calculations for promotes

---

## Core Components

### 1. Portfolio Class (`Portfolio.py`)

**Purpose:** The Portfolio class serves as the central orchestrator, managing multiple properties, loans, preferred equity positions, and portfolio-level cash flows.

**Key Features:**

#### Data Management
- **Property Management**: Add, remove, and update multiple properties
- **Loan Management**: Track both secured (property-level) and unsecured (fund-level) loans
- **Preferred Equity**: Manage preferred equity investments
- **Capital Activity**: Track capital calls, redemptions, distributions, and DRIP

#### Cash Flow Analysis
- **Portfolio Cash Flows**: Aggregate cash flows across all properties and loans
- **Net Asset Value (NAV)**: Calculate monthly NAV including management fees
- **Leverage Metrics**: Track total, encumbered, and unencumbered leverage ratios
- **Unfunded Commitments**: Monitor remaining capital commitments

#### Valuation & Returns
- **Property Valuation**: Support for growth-based and cap rate-based valuation methods
- **Loan Valuation**: Mark-to-market valuation of loan positions
- **Income & Appreciation Returns**: Calculate quarterly income and appreciation returns
- **Performance Metrics**: Track gross income, gain/loss, and total returns

#### Data Import/Export
- **Excel Integration**: Load data from structured Excel workbooks with multiple sheets:
  - Properties
  - Cash Flows (NOI, CapEx)
  - Secured Loans
  - Unsecured Loans
  - Unsecured Loan Flows
  - Capital Flows
  - Preferred Equity
  - Promotes
- **Treasury Rates**: Fetch rates from FRED API and Chatham Financial API for loan valuation

**Key Methods:**

- `load_data()`: Master method to load all data from Excel workbook
- `get_portfolio_cash_flows_share_df()`: Generate comprehensive portfolio cash flow DataFrame
- `concat_property_cash_flows_at_share_with_unsecured_loans()`: Combine all cash flows adjusted for ownership
- `value_property_loans_at_share_with_valuer()`: Mark-to-market loan valuations
- `calculate_unfunded_commitments()`: Track unfunded capital commitments over time
- `fetch_treasury_rates()`: Retrieve current treasury rates for loan valuation

**Portfolio Metrics Calculated:**
- Net Asset Value (NAV)
- Total Leverage Ratio
- Encumbered/Unencumbered Leverage Ratios
- Quarterly Income Returns
- Quarterly Appreciation Returns
- Management Fees (quarterly)

---

### 2. Property Class (`Property.py`)

**Purpose:** Models individual real estate assets with comprehensive cash flow projections, ownership tracking, and loan management.

**Key Features:**

#### Property Attributes
- **Basic Info**: Name, type, address, building size
- **Financial Data**: Acquisition cost, disposition price, market value
- **Dates**: Acquisition, disposition, construction completion dates
- **Ownership**: Dynamic ownership tracking with buyout and partial sale support
- **Valuation Parameters**: Cap rates, exit cap rates, growth rates, CAPEX percentages

#### Cash Flow Management
- **NOI (Net Operating Income)**: Monthly NOI projections
- **CapEx**: Capital expenditure tracking
- **Promote Cash Flows**: Carried interest distributions
- **Loan Debt Service**: Interest and principal payments

#### Valuation Methods

The Property class supports two valuation approaches:

1. **Growth Method** (default):
   - Market value grows at a specified annual rate
   - CAPEX additions during construction phase
   - Formula: `Value(t) = Value(t-1) * (1 + growth_rate/12) + CAPEX(t)`

2. **Cap Rate Method**:
   - Values property by capitalizing forward 12-month NOI
   - Uses interpolated cap rate between entry and exit cap rates
   - Formula: `Value(t) = Forward_12M_NOI / Interpolated_Cap_Rate`
   - Interpolation: Linear progression from entry cap rate to exit cap rate over 120 months

#### Ownership Tracking
- **Dynamic Ownership**: Track ownership percentage changes over time
- **Partner Buyouts**: Record partner buyout transactions
- **Partial Sales**: Track partial disposition events
- **Ownership Series**: Generate time series of ownership percentages

#### Loan Integration
- **Multiple Loans**: Support multiple loans per property
- **Debt Service**: Calculate loan payments and balances
- **Encumbered Status**: Flag properties with debt

#### Promote Calculations
- **Waterfall Structures**: Support multi-tier promote structures
- **Effective Share**: Calculate LP effective ownership after promotes
- **Cash Flow Dilution**: Track dilution from promote distributions
- **IRR Optimization**: Find optimal disposition date to maximize returns

**Key Methods:**

- `grow_market_value()`: Calculate property values over analysis period
- `generate_ownership_series()`: Create time series of ownership percentages
- `adjust_cash_flows_by_ownership_df()`: Apply ownership percentages to cash flows
- `calculate_effective_share()`: Compute LP effective share after promote distributions
- `combine_loan_cash_flows_df()`: Merge property and loan cash flows
- `capitalize_forward_noi()`: Value property using forward NOI and cap rate
- `find_optimal_disposition_date()`: Identify disposition date that maximizes IRR
- `calculate_property_irr()`: Calculate property-level IRR for a given hold period

**Property Valuation Logic:**

```
IF construction_finished AND valuation_method == "cap_rate":
    # Cap Rate Method
    forward_12m_noi = sum(next 12 months of NOI)
    interpolated_cap_rate = cap_rate + (months_elapsed/120) * (exit_cap_rate - cap_rate)
    market_value = forward_12m_noi / interpolated_cap_rate
ELSE:
    # Growth Method
    monthly_growth = (1 + annual_growth_rate) ^ (1/12)
    market_value = prior_value * monthly_growth + capex_spending
```

---

### 3. Loan Class (`Loan.py`)

**Purpose:** Models debt instruments with flexible payment structures, draw/paydown schedules, and commitment tracking.

**Key Features:**

#### Loan Types & Structures
- **Secured Loans**: Property-level mortgages
- **Unsecured Loans**: Fund-level credit facilities
- **Payment Types**: Actual/360, 30/360, Actual/365 day count conventions
- **Amortization**: Interest-only and amortizing periods

#### Payment Structures
- **Interest-Only Period**: Specified number of months with interest-only payments
- **Amortization Period**: Monthly principal & interest payments
- **Interest Calculation**: Accurate day count based on payment type
- **Prepayment**: Optional early payoff
- **Foreclosure**: Model loan default scenarios

#### Commitment & Draws
- **Loan Commitment**: Total facility size
- **Draw Schedule**: Track loan draws over time
- **Unfunded Commitment**: Remaining available capacity
- **Paydowns**: Principal reductions before maturity

#### Schedule Generation
The Loan class generates detailed monthly schedules including:
- Beginning Balance
- Loan Draws
- Interest Payments (using specified day count convention)
- Scheduled Principal Payments (amortizing loans)
- Loan Paydowns (voluntary prepayments)
- Ending Balance
- Encumbered Flag

**Key Methods:**

- `generate_loan_schedule()`: Create month-by-month payment schedule
- `calculate_interest()`: Compute interest using appropriate day count convention
- `calculate_amortizing_payment()`: Calculate fixed P&I payment
- `add_loan_draw()`: Process a loan draw against available commitment
- `add_loan_paydown()`: Process voluntary principal reduction
- `calculate_unfunded()`: Track remaining commitment capacity
- `calculate_loan_market_value()`: Calculate present value of loan cash flows
- `value_loan()`: Mark-to-market using treasury rates and spread

**Loan Amortization Formula:**

```
monthly_rate = annual_rate / 12
payment = loan_balance * (monthly_rate * (1 + monthly_rate)^periods) / ((1 + monthly_rate)^periods - 1)
```

**Interest Calculation:**

```
Actual/360: Interest = Balance * Rate * Actual_Days / 360
30/360: Interest = Balance * Rate * 30 / 360
Actual/365: Interest = Balance * Rate * Actual_Days / 365
```

---

### 4. LoanValuation Class (`LoanValuation.py`)

**Purpose:** Provides mark-to-market valuation of loan positions using spread-over-treasury methodology.

**Key Features:**

#### Valuation Methodology
The valuation follows a systematic approach:

1. **Origination Spread Calculation**:
   - Compare loan note rate to treasury rate at funding (60 days prior)
   - Spread = Note Rate - Treasury Rate at Origination

2. **Current Discount Rate**:
   - Add origination spread to current treasury rate
   - Discount Rate = Current Treasury Rate + Origination Spread

3. **Present Value Calculation**:
   - Discount future loan cash flows to present value
   - Sum interest payments, principal payments, and paydowns

4. **Chatham Style Adjustment** (optional):
   - Splits difference between par and market value
   - Adjusted Value = Market Value + (Par Value - Market Value) / 2

#### Treasury Rate Management
- **FRED API Integration**: Fetch historical treasury rates
- **Chatham Financial API**: Get current market rates
- **Rate Caching**: Store rates in memory for efficiency
- **Nearest Rate Logic**: Use closest available date if exact match unavailable

**Key Methods:**

- `get_treasury_rate()`: Retrieve treasury rate for a specific date
- `calculate_spread_at_origination()`: Compute loan spread at funding
- `calculate_discount_rate()`: Determine current valuation discount rate
- `calculate_present_value()`: PV of future loan cash flows
- `calculate_loan_market_value()`: Main valuation method

**Valuation Formula:**

```
For each future cash flow:
    months_elapsed = months from valuation_date to cash_flow_date
    discount_factor = 1 / (1 + discount_rate/12)^months_elapsed
    present_value += cash_flow * discount_factor

If Chatham Style:
    adjusted_value = present_value + (par_value - present_value) / 2
```

---

### 5. PreferredEquity Class (`PreferredEquity.py`)

**Purpose:** Models preferred equity investments that are backed by underlying loan positions.

**Key Features:**

#### Preferred Equity Structure
- **Underlying Loan**: Backed by a Loan object
- **Ownership Tracking**: Dynamic ownership percentage over time
- **Cash Flow Translation**: Converts loan payments to equity returns

#### Cash Flow Mapping
The class translates loan cash flows into preferred equity terms:
- **NOI**: Interest payments from underlying loan
- **Preferred Equity Draws**: Loan draws (capital deployed)
- **Preferred Equity Repayments**: Principal payments + paydowns (capital returned)
- **Market Value**: Outstanding loan balance

#### Ownership Changes
- Track ownership percentage changes over time
- Apply ownership adjustments to all cash flows
- Generate ownership time series aligned with loan schedule

**Key Methods:**

- `add_pe_ownership_change()`: Record ownership change event
- `get_ownership_share()`: Retrieve ownership at specific date
- `generate_pe_ownership_series()`: Create ownership time series
- `generate_preferred_equity_schedule_df()`: Full ownership cash flows
- `generate_preferred_equity_schedule_share_df()`: Ownership-adjusted cash flows

**Preferred Equity Cash Flow Transformation:**

```
Underlying Loan          →  Preferred Equity
------------------          ------------------
Interest Payment        →  NOI (Income)
Loan Draw              →  Preferred Equity Draw
Principal + Paydown    →  Preferred Equity Repayment
Ending Balance         →  Market Value
```

---

### 6. CarriedInterest Class (`CarriedInterest.py`)

**Purpose:** Calculates waterfall distributions for carried interest (promote) structures with multiple hurdle rates.

**Key Features:**

#### Waterfall Mechanics
The class implements sophisticated waterfall distribution logic:

1. **Initial Capital Allocation**:
   - Negative cash flows (contributions) split by first tier ratio
   - Typically 90% LP / 10% GP for contributions

2. **Return of Capital + Preferred Return**:
   - Positive cash flows first return LP capital plus hurdle return
   - Calculate future value needed to meet hurdle rate
   - Distribute until hurdle is met

3. **Catch-Up Tiers** (if applicable):
   - After hurdle met, GP "catches up" to target split
   - May have multiple tiers with different splits

4. **Residual Split**:
   - Remaining distributions split per final tier ratio
   - Common structures: 80/20, 70/30, etc.

#### Multi-Tier Support
- Support for unlimited number of tiers
- Each tier has:
  - Hurdle Rate (IRR threshold)
  - LP Distribution Ratio
  - GP Distribution Ratio (calculated as 1 - LP ratio)

#### Performance Metrics
The class calculates comprehensive metrics:
- **IRR**: XIRR for deal, LP, and GP
- **Multiple**: Distributions / Contributions
- **Profit**: Total net cash flow
- **Effective Share**: LP's effective ownership percentage after promote

**Key Methods:**

- `calculate()`: Main waterfall calculation
- `_initial_allocation()`: Allocate contributions
- `_tier_distribution()`: Distribute returns through tiers
- `_future_value()`: Calculate FV needed for hurdle
- `xirr()`: Calculate internal rate of return
- `xnpv()`: Calculate net present value
- `get_lp_effective_share()`: Get LP's effective ownership

**Waterfall Distribution Logic:**

```
For each positive cash flow:
    remaining = cash_flow

    For each tier:
        # Calculate LP capital + preferred return
        fv_needed = LP_cash_flows_NPV * (1 + hurdle_rate)^time

        # Allocate to LP at tier ratio
        lp_allocation = min(fv_needed, remaining * tier.lp_ratio)

        # Allocate to GP at tier ratio
        gp_allocation = lp_allocation * (tier.gp_ratio / tier.lp_ratio)

        remaining -= (lp_allocation + gp_allocation)

        if remaining <= 0:
            break

    # Allocate excess at final tier split
    if remaining > 0:
        lp_allocation += remaining * final_tier.lp_ratio
        gp_allocation += remaining * final_tier.gp_ratio
```

**Example Waterfall Structure:**

```
Tier 1: Return of Capital + 8% Preferred Return (90/10 split)
Tier 2: 12% IRR Catch-Up (70/30 split)
Tier 3: Residual (70/30 split)
```

---

## Data Flow

### 1. Data Import Process

```
Excel Workbook
    ├── Properties Sheet → Property objects
    ├── Cash Flows Sheet → NOI & CapEx by property
    ├── Secured Loans Sheet → Loan objects (property-level)
    ├── Unsecured Loans Sheet → Loan objects (fund-level)
    ├── Unsecured Loan Flows → Draw/paydown schedules
    ├── Capital Flows → Capital calls, redemptions, distributions
    ├── Preferred Equity → PreferredEquity objects
    └── Promotes → Promote tier structures & cash flows
```

### 2. Portfolio Assembly

```
Portfolio.load_data()
    ├── Load properties → Create Property objects
    ├── Load cash flows → Populate NOI & CapEx dictionaries
    ├── Load secured loans → Create Loan objects, link to properties
    ├── Load unsecured loans → Create fund-level Loan objects
    ├── Load loan flows → Process draws & paydowns
    ├── Load capital flows → Track LP capital activity
    ├── Load preferred equity → Create PreferredEquity objects
    ├── Load promotes → Configure waterfall tiers
    ├── Calculate unfunded equity → Track construction commitments
    └── Fetch treasury rates → For loan valuation
```

### 3. Cash Flow Generation

```
Property Level:
    Property.get_cash_flows_df()
        ├── Market value growth/decline
        ├── NOI & CapEx
        ├── Acquisition & disposition
        ├── Partner buyouts & partial sales
        └── Loan debt service

Loan Level:
    Loan.generate_loan_schedule_df()
        ├── Loan draws
        ├── Interest payments
        ├── Principal amortization
        └── Paydowns

Preferred Equity Level:
    PreferredEquity.generate_preferred_equity_schedule_share_df()
        ├── Interest income (from loan)
        ├── Capital draws
        └── Capital repayments

Portfolio Level:
    Portfolio.concat_property_cash_flows_at_share_with_unsecured_loans()
        ├── Aggregate all property cash flows
        ├── Apply ownership adjustments
        ├── Add unsecured loan cash flows
        ├── Add preferred equity cash flows
        └── Calculate portfolio metrics
```

### 4. Valuation Process

```
Property Valuation:
    IF valuation_method == "growth":
        Value = Prior_Value * Growth_Factor + CapEx
    ELSE IF valuation_method == "cap_rate":
        Value = Forward_12M_NOI / Interpolated_Cap_Rate

Loan Valuation:
    LoanValuation.calculate_loan_market_value()
        ├── Fetch treasury rate (60 days before funding)
        ├── Calculate origination spread
        ├── Get current treasury rate
        ├── Calculate discount rate
        ├── Discount future cash flows
        └── Apply Chatham adjustment (optional)

Portfolio NAV:
    NAV = Sum(Property_Values) - Sum(Loan_Balances) + Cash - Preferred_Equity
```

### 5. Return Calculation

```
Portfolio.calculate_income_and_gains()
    ├── Calculate market value changes
    ├── Separate gain/loss from income
    ├── Track capital activity (calls, redemptions)
    ├── Calculate trailing 3-month income
    ├── Calculate trailing 3-month gains
    ├── Compute quarterly returns:
        Income Return = T3_Income / (Beginning_NAV + Capital_Activity)
        Appreciation Return = T3_Gains / (Beginning_NAV + Capital_Activity)
        Total Return = Income Return + Appreciation Return
```

---

## Key Calculations

### 1. Net Asset Value (NAV)

```python
NAV = Market_Value - Loan_Balance + Cash - Management_Fee

Where:
- Market_Value = Sum of all property market values
- Loan_Balance = Sum of all loan ending balances (secured + unsecured)
- Cash = Beginning cash + Net cash flows - Management fees
- Management_Fee = NAV * Fee_Rate / 4 (quarterly)
```

### 2. Leverage Ratios

```python
# Total Leverage
Total_Leverage = Total_Debt / (Market_Value + Cash)

# Unencumbered Leverage
Unencumbered_Leverage = Unsecured_Debt / Unencumbered_Market_Value

# Encumbered Leverage
Encumbered_Leverage = Secured_Debt / Encumbered_Market_Value
```

### 3. Quarterly Returns

```python
# Trailing 3-month calculations
T3_Income = Sum of gross income over past 3 months
T3_Gains = Sum of gains/losses over past 3 months
Beginning_NAV = NAV from 3 months ago
Capital_Activity = Sum of (capital_calls + DRIP - redemptions) over past 3 months

# Return calculations
Income_Return = T3_Income / (Beginning_NAV + Capital_Activity)
Appreciation_Return = T3_Gains / (Beginning_NAV + Capital_Activity)
Total_Return = Income_Return + Appreciation_Return
```

### 4. Unfunded Commitments

```python
For each month:
    IF month == first_month:
        Unfunded = Initial_Commitment
    ELSE:
        Unfunded = Prior_Month_Unfunded - Capital_Calls + Redemptions
```

### 5. Property IRR

```python
cash_flows = [-initial_investment]
For each month in holding period:
    cash_flow = NOI - CapEx
    IF disposition_month:
        cash_flow += sale_proceeds
    cash_flows.append(cash_flow)

IRR = numpy_financial.irr(cash_flows) * 12  # Annualize
```

---

## Use Cases

### 1. Portfolio Performance Tracking
- Monitor monthly NAV evolution
- Calculate quarterly income and appreciation returns
- Track leverage ratios over time
- Analyze property-level contributions

### 2. Investment Underwriting
- Model new property acquisitions
- Analyze different debt structures
- Evaluate promote/waterfall implications
- Optimize disposition timing

### 3. Loan Portfolio Management
- Track loan draws and paydowns
- Monitor unfunded commitments
- Calculate mark-to-market valuations
- Assess interest rate sensitivity

### 4. LP/GP Reporting
- Calculate carried interest distributions
- Determine effective ownership percentages
- Report on capital calls and distributions
- Provide waterfall projections

### 5. Scenario Analysis
- Compare growth vs. cap rate valuation methods
- Model partial sales and partner buyouts
- Analyze impact of different exit timing
- Evaluate refinancing alternatives

---

## Technical Details

### Date Handling
- All dates are normalized to month-end using `ensure_date()` and `get_end_of_month()`
- Handles pandas Timestamps, datetime objects, and date objects
- Consistent month-end alignment across all calculations

### Data Structures
- **OrderedDict**: Used for loan schedules to maintain chronological order
- **Dictionaries**: Used for cash flow storage (date → amount)
- **DataFrames**: Used for aggregated reporting and analysis
- **Lists**: Used for time series (month lists, ownership changes)

### Error Handling
- Logging warnings for data inconsistencies
- Validation of loan dates vs. property disposition dates
- Checks for negative cash balances
- Verification of ownership percentages (0-1 range)

### Performance Considerations
- Treasury rates cached to avoid repeated API calls
- Loan schedules regenerated only when draws/paydowns change
- Market value calculations optimized with pre-computed growth factors

---

## Dependencies

### Required Python Packages
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computations
- **numpy_financial**: Financial calculations (IRR, NPV)
- **scipy**: Optimization routines (XIRR calculation)
- **requests**: API calls for treasury rates
- **dateutil**: Date manipulation utilities
- **logging**: Error and warning tracking

### External Data Sources
- **FRED API**: Federal Reserve Economic Data (treasury rates)
- **Chatham Financial API**: Current market swap rates

---

## File Structure

```
portfolio_manager/
│
├── __init__.py                      # Package initialization
├── Portfolio.py                     # Main portfolio management class
├── Property.py                      # Individual property modeling
├── Loan.py                          # Loan and debt instruments
├── LoanValuation.py                 # Mark-to-market loan valuation
├── PreferredEquity.py               # Preferred equity positions
├── CarriedInterest.py               # Promote waterfall calculations
└── Property_Import_Template.xlsx   # Data import template
```

---

## Excel Import Template Structure

The system expects an Excel workbook with the following sheets:

### Properties Sheet
Columns: id, name, property_type, acquisition_date, disposition_date, acquisition_cost, disposition_price, address, city, state, zipcode, building_size, market_value, analysis_date, analysis_length, market_value_growth, ownership, construction_end, equity_commitment, partner_buyout_cost, partner_buyout_date, partner_buyout_percent, partial_sale_date, partial_sale_percent, partial_sale_proceeds, encumbered, cap_rate, exit_cap_rate, capex_percent_of_noi, promote, upper_tier_share

### Cash Flows Sheet
Columns: id (property_id), date, cash_flow (noi/capex), amount

### Secured Loans Sheet
Columns: id, property_id, loan_amount, rate, fund_date, maturity_date, payment_type, interest_only_periods, amortizing_periods, commitment, prepayment_date, foreclosure_date, market_rate, fixed_floating

### Unsecured Loans Sheet
Columns: id, loan_amount, rate, fund_date, maturity_date, payment_type, interest_only_periods, amortizing_periods, commitment, prepayment_date, foreclosure_date, market_rate, fixed_floating

### Unsecured Loan Flows Sheet
Columns: id (loan_id), date, flow_type (draw/paydown), amount

### Capital Flows Sheet
Columns: date, cash_flow (capital call/redemption/distribution/drip), amount

### Preferred Equity Sheet
Columns: id, property_id, loan_id, ownership_share

### Promotes Sheet
Columns: property_id, tier_number, hurdle_rate, lp_distribution (for tier structure)
         property_id_, date, cash_flow (for promote cash flows)

---

## Example Workflow

### Complete Portfolio Analysis

```python
from portfolio_manager.Portfolio import Portfolio
from datetime import date

# 1. Initialize portfolio
portfolio = Portfolio(
    analysis_start_date=date(2024, 1, 31),
    analysis_end_date=date(2029, 12, 31),
    initial_unfunded_equity=50_000_000
)

# 2. Configure portfolio
portfolio.set_file_path('data/portfolio_data.xlsx')
portfolio.set_beginning_nav(100_000_000)
portfolio.set_fee(0.0125)  # 1.25% annual management fee
portfolio.set_valuation_method('growth')

# 3. Load data
portfolio.load_data()

# 4. Generate portfolio cash flows
cash_flows = portfolio.get_portfolio_cash_flows_share_df()

# 5. Value loan portfolio
loan_values = portfolio.value_property_loans_at_share_with_valuer(
    as_of_date=date(2024, 12, 31)
)

# 6. Get unfunded commitments
unfunded = portfolio.get_unfunded_commitments_df()

# 7. Analyze property-level performance
for prop_id, property in portfolio.properties.items():
    irr, cash_flows = property.calculate_property_irr()
    print(f"{property.name}: IRR = {irr:.2%}")
```

---

## Conclusion

The Portfolio Manager is a sophisticated system designed for institutional real estate investment management. It handles complex scenarios including:

- Multi-property portfolios with varying ownership structures
- Secured and unsecured debt facilities
- Preferred equity investments
- Multi-tier carried interest waterfalls
- Dynamic valuation methodologies
- Comprehensive performance reporting

The modular architecture allows for flexible modeling while maintaining data integrity and calculation accuracy across all investment components.

---

## Notes on Valuation Methods

### Growth Method
Best for stabilized assets with predictable appreciation. Uses compound growth with CAPEX additions during development.

### Cap Rate Method
Best for income-producing properties where cap rate compression/expansion is expected. Values based on forward NOI and interpolated cap rates.

### Loan Valuation
Uses spread-over-treasury methodology consistent with institutional investment practices. Chatham-style adjustment provides conservative middle-ground between par and market value.

---

## Common Calculations Reference

### Monthly Growth Factor
```python
monthly_factor = (1 + annual_rate) ** (1/12)
```

### Cap Rate Interpolation
```python
months_elapsed = current_month_index
fraction = min(months_elapsed / 120, 1)
current_cap_rate = entry_cap + fraction * (exit_cap - entry_cap)
```

### Discount Factor
```python
months = periods_from_valuation_date
discount_factor = 1 / (1 + annual_rate/12) ** months
```

### XIRR (Irregular Cash Flows)
```python
NPV = sum(CF_i / (1 + rate)^(days_i/365) for each cash flow)
XIRR = rate where NPV = 0
```

---

*Document generated to explain the Portfolio Manager codebase structure and functionality.*
