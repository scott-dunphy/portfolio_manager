from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import pandas as pd
from database import db
from models import Portfolio, Property, Loan, PreferredEquity
from datetime import datetime

bp = Blueprint('upload', __name__, url_prefix='/api/upload')

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/excel', methods=['POST'])
def upload_excel():
    """Upload and parse Excel file for property data"""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    portfolio_id = request.form.get('portfolio_id', type=int)

    if not portfolio_id:
        return jsonify({"error": "portfolio_id is required"}), 400

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join('uploads', filename)
        file.save(filepath)

        try:
            # Read Excel file
            df = pd.read_excel(filepath, sheet_name='Property_Import')

            properties_created = []
            loans_created = []
            errors = []

            # Process each row
            for idx, row in df.iterrows():
                try:
                    # Create property
                    property_data = {
                        'portfolio_id': portfolio_id,
                        'property_id': str(row.get('Property_ID', f'PROP_{idx}')),
                        'property_name': row.get('Property_Name', ''),
                        'property_type': row.get('Property_Type', ''),
                        'address': row.get('Address', ''),
                        'city': row.get('City', ''),
                        'state': row.get('State', ''),
                        'zip_code': str(row.get('Zip_Code', '')),
                        'purchase_price': float(row.get('Purchase_Price', 0)) if pd.notna(row.get('Purchase_Price')) else None,
                        'building_size': float(row.get('Building_Size', 0)) if pd.notna(row.get('Building_Size')) else None,
                        'exit_cap_rate': float(row.get('Exit_Cap_Rate', 0)) if pd.notna(row.get('Exit_Cap_Rate')) else None,
                        'year_1_cap_rate': float(row.get('Year_1_Cap_Rate', 0)) if pd.notna(row.get('Year_1_Cap_Rate')) else None,
                        'noi_growth_rate': float(row.get('NOI_Growth_Rate', 0)) if pd.notna(row.get('NOI_Growth_Rate')) else None,
                        'initial_noi': float(row.get('Initial_NOI', 0)) if pd.notna(row.get('Initial_NOI')) else None,
                    }

                    # Handle dates
                    if pd.notna(row.get('Purchase_Date')):
                        try:
                            property_data['purchase_date'] = pd.to_datetime(row['Purchase_Date']).date()
                        except:
                            pass

                    if pd.notna(row.get('Exit_Date')):
                        try:
                            property_data['exit_date'] = pd.to_datetime(row['Exit_Date']).date()
                        except:
                            pass

                    property = Property(**property_data)
                    db.session.add(property)
                    db.session.flush()  # Get the property ID

                    properties_created.append(property.property_id)

                    # Create loan if loan data exists
                    if pd.notna(row.get('Loan_Amount')):
                        loan_data = {
                            'portfolio_id': portfolio_id,
                            'property_id': property.id,
                            'loan_id': str(row.get('Loan_ID', f'LOAN_{idx}')),
                            'loan_name': row.get('Loan_Name', f'Loan for {property_data["property_name"]}'),
                            'principal_amount': float(row.get('Loan_Amount', 0)),
                            'interest_rate': float(row.get('Interest_Rate', 0)) if pd.notna(row.get('Interest_Rate')) else 0.0,
                            'payment_frequency': 'monthly',
                            'loan_type': row.get('Loan_Type', 'Senior'),
                            'io_period_months': int(row.get('IO_Period_Months', 0)) if pd.notna(row.get('IO_Period_Months')) else 0,
                        }

                        # Handle loan dates
                        if pd.notna(row.get('Loan_Origination_Date')):
                            try:
                                loan_data['origination_date'] = pd.to_datetime(row['Loan_Origination_Date']).date()
                            except:
                                loan_data['origination_date'] = datetime.now().date()
                        else:
                            loan_data['origination_date'] = datetime.now().date()

                        if pd.notna(row.get('Loan_Maturity_Date')):
                            try:
                                loan_data['maturity_date'] = pd.to_datetime(row['Loan_Maturity_Date']).date()
                            except:
                                loan_data['maturity_date'] = datetime.now().date()
                        else:
                            loan_data['maturity_date'] = datetime.now().date()

                        loan = Loan(**loan_data)
                        db.session.add(loan)
                        loans_created.append(loan.loan_id)

                except Exception as e:
                    errors.append(f"Row {idx + 2}: {str(e)}")

            db.session.commit()

            # Clean up uploaded file
            os.remove(filepath)

            return jsonify({
                "message": "File processed successfully",
                "properties_created": len(properties_created),
                "loans_created": len(loans_created),
                "errors": errors
            }), 201

        except Exception as e:
            db.session.rollback()
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({"error": f"Error processing file: {str(e)}"}), 400

    return jsonify({"error": "Invalid file type"}), 400

@bp.route('/template', methods=['GET'])
def download_template():
    """Download the Excel template"""
    template_path = os.path.join('..', 'Property_Import_Template.xlsx')
    if os.path.exists(template_path):
        from flask import send_file
        return send_file(template_path, as_attachment=True)
    else:
        return jsonify({"error": "Template not found"}), 404
