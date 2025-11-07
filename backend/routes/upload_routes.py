from datetime import datetime
from io import BytesIO

import pandas as pd
from flask import Blueprint, jsonify, request, send_file

from database import db
from models import Loan, Property, PropertyManualCashFlow
from services.cash_flow_service import regenerate_loan_cash_flows, regenerate_property_cash_flows
from services.import_template import build_import_template

bp = Blueprint('upload', __name__, url_prefix='/api/upload')

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}


@bp.route('/excel', methods=['POST'])
def upload_excel():
    """Upload and parse Excel file for property & loan data."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    portfolio_id = request.form.get('portfolio_id', type=int)

    if not portfolio_id:
        return jsonify({"error": "portfolio_id is required"}), 400
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if not _allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    file_bytes = file.read()
    try:
        excel = pd.ExcelFile(BytesIO(file_bytes))
    except Exception as exc:
        return jsonify({"error": f"Invalid Excel file: {exc}"}), 400

    if "Properties" not in excel.sheet_names:
        return jsonify({"error": "Sheet 'Properties' is required."}), 400

    properties_df = excel.parse("Properties")
    loans_df = excel.parse("Loans") if "Loans" in excel.sheet_names else pd.DataFrame()
    manual_df = excel.parse("Manual_NOI_Capex") if "Manual_NOI_Capex" in excel.sheet_names else pd.DataFrame()

    result = _process_import(portfolio_id, properties_df, loans_df, manual_df)
    status = 201 if not result["errors"] else 207
    return jsonify(result), status


@bp.route('/template', methods=['GET'])
def download_template():
    """Generate and download the Excel template."""
    stream = build_import_template()
    return send_file(
        stream,
        download_name='Portfolio_Import_Template.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _parse_date(value):
    if pd.isna(value) or value == '':
        return None
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def _parse_float(value):
    if pd.isna(value) or value == '':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_int(value):
    if pd.isna(value) or value == '':
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if pd.isna(value) or value == '':
        return False
    return str(value).strip().lower() in {'1', 'true', 't', 'yes', 'y'}


def _process_import(portfolio_id, properties_df, loans_df, manual_df):
    errors = []
    properties_created = 0
    properties_updated = 0
    loans_created = 0
    loans_updated = 0

    property_map = {}
    touched_properties = set()
    touched_loans = set()

    def get_property(prop_id):
        if not prop_id:
            return None
        if prop_id in property_map:
            return property_map[prop_id]
        prop = Property.query.filter_by(portfolio_id=portfolio_id, property_id=prop_id).first()
        if prop:
            property_map[prop_id] = prop
        return prop

    # Properties sheet
    for idx, row in properties_df.iterrows():
        property_id = str(row.get('Property_ID')).strip() if pd.notna(row.get('Property_ID')) else None
        if not property_id:
            errors.append(f"Properties row {idx + 2}: Property_ID is required.")
            continue

        property_obj = get_property(property_id)
        is_new = property_obj is None
        if is_new:
            property_obj = Property(
                portfolio_id=portfolio_id,
                property_id=property_id,
                property_name=row.get('Property_Name') or property_id,
            )
            db.session.add(property_obj)
            properties_created += 1
        else:
            properties_updated += 1

        property_obj.property_name = row.get('Property_Name') or property_obj.property_name
        property_obj.property_type = row.get('Property_Type') or property_obj.property_type
        property_obj.address = row.get('Address') or property_obj.address
        property_obj.city = row.get('City') or property_obj.city
        property_obj.state = row.get('State') or property_obj.state
        property_obj.zip_code = str(row.get('Zip_Code')) if pd.notna(row.get('Zip_Code')) else property_obj.zip_code
        property_obj.purchase_price = _parse_float(row.get('Purchase_Price')) or property_obj.purchase_price
        property_obj.building_size = _parse_float(row.get('Building_Size')) or property_obj.building_size
        property_obj.exit_cap_rate = _parse_float(row.get('Exit_Cap_Rate')) or property_obj.exit_cap_rate
        property_obj.year_1_cap_rate = _parse_float(row.get('Year_1_Cap_Rate')) or property_obj.year_1_cap_rate
        property_obj.noi_growth_rate = _parse_float(row.get('NOI_Growth_Rate')) or property_obj.noi_growth_rate
        property_obj.initial_noi = _parse_float(row.get('Initial_NOI')) or property_obj.initial_noi
        capex_pct = _parse_float(row.get('Capex_Percent_of_NOI'))
        if capex_pct is not None:
            property_obj.capex_percent_of_noi = capex_pct
        ownership_percent = _parse_float(row.get('Ownership_Percent'))
        if ownership_percent is not None:
            property_obj.ownership_percent = ownership_percent
        property_obj.purchase_date = _parse_date(row.get('Purchase_Date')) or property_obj.purchase_date
        property_obj.exit_date = _parse_date(row.get('Exit_Date')) or property_obj.exit_date
        valuation_method = row.get('Valuation_Method')
        if isinstance(valuation_method, str) and valuation_method.strip():
            property_obj.valuation_method = valuation_method.strip()
        property_obj.use_manual_noi_capex = _parse_bool(row.get('Use_Manual_NOI_Capex'))

        db.session.flush()
        property_map[property_id] = property_obj
        touched_properties.add(property_obj)

    # Manual overrides sheet
    if not manual_df.empty:
        manual_group = {}
        for idx, row in manual_df.iterrows():
            prop_id = str(row.get('Property_ID')).strip() if pd.notna(row.get('Property_ID')) else None
            year = _parse_int(row.get('Year'))
            if not prop_id or not year:
                errors.append(f"Manual_NOI_Capex row {idx + 2}: Property_ID and Year are required.")
                continue
            frequency = (row.get('Frequency') or 'annual').strip().lower()
            month = _parse_int(row.get('Month (1-12, required if monthly)'))
            if frequency == 'monthly' and (month is None or not 1 <= month <= 12):
                errors.append(f"Manual_NOI_Capex row {idx + 2}: Month (1-12) required for monthly entries.")
                continue
            manual_group.setdefault(prop_id, []).append(
                {
                    "year": year,
                    "month": month if frequency == 'monthly' else None,
                    "annual_noi": _parse_float(row.get('NOI')),
                    "annual_capex": _parse_float(row.get('Capex')),
                }
            )

        for prop_id, entries in manual_group.items():
            property_obj = get_property(prop_id)
            if not property_obj:
                errors.append(f"Manual_NOI_Capex: Property_ID '{prop_id}' not found in portfolio.")
                continue
            PropertyManualCashFlow.query.filter_by(property_id=property_obj.id).delete()
            for entry in entries:
                db.session.add(
                    PropertyManualCashFlow(
                        property_id=property_obj.id,
                        year=entry['year'],
                        month=entry['month'],
                        annual_noi=entry['annual_noi'],
                        annual_capex=entry['annual_capex'],
                    )
                )
            property_obj.use_manual_noi_capex = True
            touched_properties.add(property_obj)

    # Loans sheet
    for idx, row in loans_df.iterrows():
        loan_id = str(row.get('Loan_ID')).strip() if pd.notna(row.get('Loan_ID')) else None
        if not loan_id:
            errors.append(f"Loans row {idx + 2}: Loan_ID is required.")
            continue

        prop_id = str(row.get('Property_ID')).strip() if pd.notna(row.get('Property_ID')) else None
        property_obj = get_property(prop_id)
        if not property_obj:
            errors.append(f"Loans row {idx + 2}: Property_ID '{prop_id}' not found.")
            continue

        loan_obj = Loan.query.filter_by(portfolio_id=portfolio_id, loan_id=loan_id).first()
        is_new_loan = loan_obj is None
        if is_new_loan:
            loan_obj = Loan(
                portfolio_id=portfolio_id,
                property_id=property_obj.id,
                loan_id=loan_id,
                loan_name=row.get('Loan_Name') or loan_id,
                principal_amount=_parse_float(row.get('Principal_Amount')) or 0.0,
                interest_rate=_parse_float(row.get('Interest_Rate')) or 0.0,
                rate_type=(row.get('Rate_Type') or 'fixed').lower(),
                sofr_spread=_parse_float(row.get('SOFR_Spread')) or 0.0,
                origination_date=_parse_date(row.get('Origination_Date')) or datetime.utcnow().date(),
                maturity_date=_parse_date(row.get('Maturity_Date')) or datetime.utcnow().date(),
                payment_frequency=(row.get('Payment_Frequency') or 'monthly').lower(),
                loan_type=row.get('Loan_Type'),
                amortization_period_months=_parse_int(row.get('Amortization_Period_Months')),
                io_period_months=_parse_int(row.get('IO_Period_Months')) or 0,
                origination_fee=_parse_float(row.get('Origination_Fee')) or 0.0,
                exit_fee=_parse_float(row.get('Exit_Fee')) or 0.0,
            )
            db.session.add(loan_obj)
            loans_created += 1
        else:
            loans_updated += 1
            loan_obj.property_id = property_obj.id
            loan_obj.loan_name = row.get('Loan_Name') or loan_obj.loan_name
            principal = _parse_float(row.get('Principal_Amount'))
            if principal is not None:
                loan_obj.principal_amount = principal
            rate_type = (row.get('Rate_Type') or loan_obj.rate_type or 'fixed').lower()
            loan_obj.rate_type = rate_type
            if rate_type == 'floating':
                spread = _parse_float(row.get('SOFR_Spread'))
                if spread is not None:
                    loan_obj.sofr_spread = spread
            interest_rate = _parse_float(row.get('Interest_Rate'))
            if interest_rate is not None and rate_type != 'floating':
                loan_obj.interest_rate = interest_rate
            orig_date = _parse_date(row.get('Origination_Date'))
            if orig_date:
                loan_obj.origination_date = orig_date
            mat_date = _parse_date(row.get('Maturity_Date'))
            if mat_date:
                loan_obj.maturity_date = mat_date
            payment_frequency = row.get('Payment_Frequency')
            if isinstance(payment_frequency, str) and payment_frequency.strip():
                loan_obj.payment_frequency = payment_frequency.strip().lower()
            loan_type = row.get('Loan_Type')
            if isinstance(loan_type, str) and loan_type.strip():
                loan_obj.loan_type = loan_type.strip()
            amort = _parse_int(row.get('Amortization_Period_Months'))
            if amort is not None:
                loan_obj.amortization_period_months = amort
            io_months = _parse_int(row.get('IO_Period_Months'))
            if io_months is not None:
                loan_obj.io_period_months = io_months
            orig_fee = _parse_float(row.get('Origination_Fee'))
            if orig_fee is not None:
                loan_obj.origination_fee = orig_fee
            exit_fee = _parse_float(row.get('Exit_Fee'))
            if exit_fee is not None:
                loan_obj.exit_fee = exit_fee

        touched_loans.add(loan_obj)

    try:
        for prop in touched_properties:
            regenerate_property_cash_flows(prop, commit=False)
        for loan in touched_loans:
            regenerate_loan_cash_flows(loan, commit=False)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        errors.append(f"Failed to regenerate cash flows: {exc}")

    return {
        "message": "File processed successfully" if not errors else "File processed with warnings",
        "properties_created": properties_created,
        "properties_updated": properties_updated,
        "loans_created": loans_created,
        "loans_updated": loans_updated,
        "errors": errors,
    }
