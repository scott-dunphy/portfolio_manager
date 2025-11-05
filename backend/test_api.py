#!/usr/bin/env python3
"""
Simple test script to verify backend API is working
Run this after starting the Flask server
"""

import requests
import json
from datetime import date, timedelta

BASE_URL = 'http://localhost:5000'

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f'{BASE_URL}/health')
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_create_portfolio():
    """Test creating a portfolio"""
    print("\nTesting portfolio creation...")

    start_date = date.today()
    end_date = start_date + timedelta(days=365)

    data = {
        'name': 'Test Portfolio',
        'analysis_start_date': start_date.isoformat(),
        'analysis_end_date': end_date.isoformat(),
        'initial_unfunded_equity': 1000000,
        'beginning_cash': 500000,
        'fee': 0.02,
        'beginning_nav': 5000000,
        'valuation_method': 'growth'
    }

    response = requests.post(f'{BASE_URL}/api/portfolios', json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 201

def test_get_portfolios():
    """Test getting all portfolios"""
    print("\nTesting get all portfolios...")
    response = requests.get(f'{BASE_URL}/api/portfolios')
    print(f"Status: {response.status_code}")
    portfolios = response.json()
    print(f"Found {len(portfolios)} portfolio(s)")
    if portfolios:
        print(f"First portfolio: {json.dumps(portfolios[0], indent=2)}")
    return response.status_code == 200

if __name__ == '__main__':
    print("=" * 50)
    print("Backend API Test Suite")
    print("=" * 50)

    try:
        # Test health
        if not test_health():
            print("\n❌ Health check failed! Make sure the Flask server is running.")
            exit(1)

        print("\n✓ Health check passed!")

        # Test portfolio endpoints
        if test_create_portfolio():
            print("\n✓ Portfolio creation passed!")
        else:
            print("\n❌ Portfolio creation failed!")

        if test_get_portfolios():
            print("\n✓ Get portfolios passed!")
        else:
            print("\n❌ Get portfolios failed!")

        print("\n" + "=" * 50)
        print("All tests completed!")
        print("=" * 50)

    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to backend server!")
        print("Make sure the Flask server is running on http://localhost:5000")
        print("\nTo start the server:")
        print("  cd backend")
        print("  python app.py")
