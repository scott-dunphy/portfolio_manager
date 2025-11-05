from flask import Flask, request, jsonify
from flask_cors import CORS
from database import db
from datetime import datetime
import os

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portfolio_manager.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    CORS(app)

    # Import routes
    from routes import portfolio_routes, property_routes, loan_routes, preferred_equity_routes, cash_flow_routes, upload_routes

    # Register blueprints
    app.register_blueprint(portfolio_routes.bp)
    app.register_blueprint(property_routes.bp)
    app.register_blueprint(loan_routes.bp)
    app.register_blueprint(preferred_equity_routes.bp)
    app.register_blueprint(cash_flow_routes.bp)
    app.register_blueprint(upload_routes.bp)

    return app

app = create_app()

@app.route('/')
def index():
    return jsonify({"message": "Portfolio Manager API", "version": "1.0"})

@app.route('/api/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
