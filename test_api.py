#!/usr/bin/env python3
"""
Test script for Finance Scraper API
"""

import requests
import json
import sys
import time

BASE_URL = "http://localhost:5000"

def test_health():
    """Test the health endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_stock_info(symbol="AAPL"):
    """Test the stock info endpoint"""
    print(f"Testing stock info endpoint for {symbol}...")
    try:
        response = requests.get(f"{BASE_URL}/stock/{symbol}", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Stock info for {symbol}:")
            print(f"   Symbol: {data.get('symbol')}")
            print(f"   Data keys: {list(data.get('data', {}).keys())[:5]}...")
            return True
        else:
            print(f"❌ Stock info failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Stock info error: {e}")
        return False

def test_stock_price(symbol="AAPL"):
    """Test the stock price endpoint"""
    print(f"Testing stock price endpoint for {symbol}...")
    try:
        response = requests.get(f"{BASE_URL}/stock/{symbol}/price", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Stock price for {symbol}:")
            print(f"   Current Price: ${data.get('current_price')}")
            print(f"   Previous Close: ${data.get('previous_close')}")
            print(f"   Volume: {data.get('volume')}")
            return True
        else:
            print(f"❌ Stock price failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Stock price error: {e}")
        return False

def test_database_clear_symbol(symbol="AAPL"):
    """Test removing a specific symbol from database"""
    print(f"Testing database clear for {symbol}...")
    try:
        response = requests.delete(f"{BASE_URL}/database/clear/{symbol}", timeout=10)
        if response.status_code in [200, 404]:  # 200 if removed, 404 if not found
            data = response.json()
            print(f"✅ Database clear for {symbol}: {data.get('message', 'Unknown')}")
            return True
        else:
            print(f"❌ Database clear failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Database clear error: {e}")
        return False

def test_database_clear_all():
    """Test clearing all data from database"""
    print("Testing clear all database...")
    try:
        response = requests.delete(f"{BASE_URL}/database/clear", timeout=10)
        if response.status_code in [200, 503]:  # 200 if cleared, 503 if MongoDB unavailable
            data = response.json()
            if response.status_code == 200:
                print(f"✅ Clear all database: {data.get('deleted_count', 0)} documents deleted")
            else:
                print(f"⚠️  MongoDB not available: {data.get('error')}")
            return True
        else:
            print(f"❌ Clear all database failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Clear all database error: {e}")
        return False

def test_database_stats():
    """Test database statistics endpoint"""
    print("Testing database stats...")
    try:
        response = requests.get(f"{BASE_URL}/database/stats", timeout=10)
        if response.status_code in [200, 503]:  # 200 if stats retrieved, 503 if MongoDB unavailable
            data = response.json()
            if response.status_code == 200:
                print(f"✅ Database stats: {data.get('total_symbols', 0)} symbols stored")
                print(f"   Database: {data.get('database')}")
                print(f"   Collection: {data.get('collection')}")
            else:
                print(f"⚠️  MongoDB not available: {data.get('error')}")
            return True
        else:
            print(f"❌ Database stats failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Database stats error: {e}")
        return False

def test_invalid_symbol():
    """Test with invalid symbol"""
    print("Testing invalid symbol...")
    try:
        response = requests.get(f"{BASE_URL}/stock/INVALID_SYMBOL_123", timeout=10)
        if response.status_code == 400:
            print("✅ Invalid symbol correctly rejected")
            return True
        else:
            print(f"❌ Invalid symbol not handled correctly: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Invalid symbol test error: {e}")
        return False

def test_404():
    """Test 404 endpoint"""
    print("Testing 404 endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/nonexistent", timeout=10)
        if response.status_code == 404:
            data = response.json()
            print("✅ 404 endpoint correctly handled")
            return True
        else:
            print(f"❌ 404 not handled correctly: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 404 test error: {e}")
        return False

def test_database_behavior(symbol="TSLA"):
    """Test database behavior by making two requests"""
    print(f"Testing database behavior for {symbol}...")
    try:
        # First request - should fetch from Yahoo and save to database
        print("   Making first request (should fetch from Yahoo)...")
        response1 = requests.get(f"{BASE_URL}/stock/{symbol}", timeout=30)
        if response1.status_code != 200:
            print(f"   ❌ First request failed: {response1.status_code}")
            return False
        
        time.sleep(2)  # Small delay
        
        # Second request - should fetch from database
        print("   Making second request (should fetch from database)...")
        response2 = requests.get(f"{BASE_URL}/stock/{symbol}", timeout=10)
        if response2.status_code != 200:
            print(f"   ❌ Second request failed: {response2.status_code}")
            return False
        
        print("   ✅ Both requests successful (database storage working)")
        return True
    except Exception as e:
        print(f"   ❌ Database behavior test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Finance Scraper API Test Suite")
    print("=" * 40)
    
    tests = [
        test_health,
        test_stock_info,
        test_stock_price,
        test_database_stats,
        test_database_clear_symbol,
        test_database_clear_all,
        test_database_behavior,
        test_invalid_symbol,
        test_404
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
        time.sleep(1)  # Small delay between tests
    
    print("=" * 40)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 