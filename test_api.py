#!/usr/bin/env python3
"""
Test script for Finance Scraper API
"""

import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:5000"  # Change this to your API URL

def test_health_check():
    """Test health check endpoint"""
    print("Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_stock_info(symbol="AAPL"):
    """Test stock info endpoint"""
    print(f"\nTesting stock info for {symbol}...")
    try:
        response = requests.get(f"{BASE_URL}/stock/{symbol}")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Symbol: {data.get('symbol')}")
            print(f"Company: {data.get('data', {}).get('longName', 'N/A')}")
            print(f"Current Price: {data.get('data', {}).get('currentPrice', 'N/A')}")
        else:
            print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_stock_price(symbol="AAPL"):
    """Test stock price endpoint"""
    print(f"\nTesting stock price for {symbol}...")
    try:
        response = requests.get(f"{BASE_URL}/stock/{symbol}/price")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Symbol: {data.get('symbol')}")
            print(f"Current Price: {data.get('current_price')}")
            print(f"Previous Close: {data.get('previous_close')}")
            print(f"Volume: {data.get('volume')}")
        else:
            print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_historical_prices(symbol="AAPL"):
    """Test historical prices endpoint"""
    print(f"\nTesting historical prices for {symbol}...")
    try:
        # Get date range for last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        params = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }
        
        response = requests.get(f"{BASE_URL}/stock/{symbol}/history", params=params)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Symbol: {data.get('symbol')}")
            print(f"Date Range: {data.get('start_date')} to {data.get('end_date')}")
            print(f"Number of price records: {data.get('count')}")
            
            # Show first few price records
            prices = data.get('prices', [])
            if prices:
                print("Sample price records:")
                for i, price in enumerate(prices[:3]):
                    print(f"  {i+1}. Date: {price.get('Date')}, Close: {price.get('Close')}, Volume: {price.get('Volume')}")
        else:
            print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_database_stats():
    """Test database stats endpoint"""
    print("\nTesting database stats...")
    try:
        response = requests.get(f"{BASE_URL}/database/stats")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total symbols: {data.get('total_symbols')}")
            print(f"Total price records: {data.get('total_price_records')}")
            print(f"Database: {data.get('database')}")
            print(f"Collections: {data.get('collections')}")
        else:
            print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_clear_database_entry(symbol="AAPL"):
    """Test clearing a specific database entry"""
    print(f"\nTesting clear database entry for {symbol}...")
    try:
        response = requests.get(f"{BASE_URL}/database/clear/{symbol}")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code in [200, 404]  # 404 is OK if symbol doesn't exist
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_clear_database():
    """Test clearing all database data"""
    print("\nTesting clear all database data...")
    try:
        response = requests.get(f"{BASE_URL}/database/clear")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_invalid_symbol():
    """Test with invalid symbol"""
    print("\nTesting invalid symbol...")
    try:
        response = requests.get(f"{BASE_URL}/stock/INVALID_SYMBOL_12345")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 404
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_invalid_historical_params():
    """Test historical prices with invalid parameters"""
    print("\nTesting historical prices with invalid parameters...")
    try:
        # Test missing parameters
        response = requests.get(f"{BASE_URL}/stock/AAPL/history")
        print(f"Missing parameters - Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Test invalid date format
        params = {
            'start_date': '2024-13-01',  # Invalid month
            'end_date': '2024-12-32'     # Invalid day
        }
        response = requests.get(f"{BASE_URL}/stock/AAPL/history", params=params)
        print(f"Invalid date format - Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Test invalid date range
        params = {
            'start_date': '2024-12-31',
            'end_date': '2024-01-01'     # Start after end
        }
        response = requests.get(f"{BASE_URL}/stock/AAPL/history", params=params)
        print(f"Invalid date range - Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_404():
    """Test 404 endpoint"""
    print("\nTesting 404 endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/nonexistent")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 404
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run all tests"""
    print("=== Finance Scraper API Tests ===\n")
    
    tests = [
        ("Health Check", test_health_check),
        ("Stock Info (AAPL)", lambda: test_stock_info("AAPL")),
        ("Stock Price (AAPL)", lambda: test_stock_price("AAPL")),
        ("Historical Prices (AAPL)", lambda: test_historical_prices("AAPL")),
        ("Stock Info (MSFT)", lambda: test_stock_info("MSFT")),
        ("Stock Price (MSFT)", lambda: test_stock_price("MSFT")),
        ("Historical Prices (MSFT)", lambda: test_historical_prices("MSFT")),
        ("Database Stats", test_database_stats),
        ("Invalid Symbol", test_invalid_symbol),
        ("Invalid Historical Parameters", test_invalid_historical_params),
        ("Clear Database Entry", lambda: test_clear_database_entry("AAPL")),
        ("Clear All Database", test_clear_database),
        ("404 Endpoint", test_404),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            if test_func():
                print(f"✅ {test_name} - PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} - FAILED")
        except Exception as e:
            print(f"❌ {test_name} - ERROR: {e}")
    
    print(f"\n{'='*50}")
    print(f"Test Results: {passed}/{total} tests passed")
    print('='*50)
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print(f"⚠️  {total - passed} test(s) failed")

if __name__ == "__main__":
    main() 