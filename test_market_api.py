#!/usr/bin/env python3
"""
Test script for the new market API endpoints
"""

import requests
import json
from datetime import datetime

def test_market_endpoints():
    """Test the new market API endpoints"""
    base_url = "http://localhost:5000"
    
    print("Testing Market API Endpoints")
    print("=" * 50)
    
    # Test 1: Market status only
    print("\n1. Testing /market/status")
    try:
        response = requests.get(f"{base_url}/market/status", timeout=30)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Market Status: {data.get('status')}")
            print(f"Market State: {data.get('market_state')}")
            print(f"Timestamp: {data.get('timestamp')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Market indices only
    print("\n2. Testing /market/indices")
    try:
        response = requests.get(f"{base_url}/market/indices", timeout=30)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            indices = data.get('indices', {})
            print(f"Available indices: {list(indices.keys())}")
            
            for index_name, index_data in indices.items():
                print(f"\n{index_name.upper()}:")
                print(f"  Symbol: {index_data.get('symbol')}")
                print(f"  Name: {index_data.get('name')}")
                print(f"  Current Price: {index_data.get('current_price')}")
                print(f"  Previous Close: {index_data.get('previous_close')}")
                print(f"  Open: {index_data.get('open')}")
                print(f"  Day High: {index_data.get('day_high')}")
                print(f"  Day Low: {index_data.get('day_low')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Complete market information
    print("\n3. Testing /market (complete)")
    try:
        response = requests.get(f"{base_url}/market", timeout=30)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Market Status: {data.get('market_status', {}).get('status')}")
            print(f"Available indices: {list(data.get('indices', {}).keys())}")
            print(f"Timestamp: {data.get('timestamp')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_market_endpoints() 