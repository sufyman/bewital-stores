#!/usr/bin/env python3
"""
Test script to discover and test Josera API endpoint.
Run this to find the exact API URL and test data extraction.
"""

import requests
import json
import sys
from urllib.parse import urljoin


def test_api_endpoint(url):
    """Test a specific API endpoint."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
        'Referer': 'https://fachhandel.josera.de/',
    }
    
    try:
        print(f"Testing: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"JSON Response Type: {type(data)}")
                
                if isinstance(data, list):
                    print(f"Found {len(data)} items in list")
                    if data:
                        print("First item keys:", list(data[0].keys()) if isinstance(data[0], dict) else "Not a dict")
                        print("Sample data:", json.dumps(data[0], indent=2)[:500] + "..." if len(str(data[0])) > 500 else json.dumps(data[0], indent=2))
                
                elif isinstance(data, dict):
                    print("Dict keys:", list(data.keys()))
                    for key in ['stores', 'dealers', 'partners', 'data', 'results']:
                        if key in data:
                            print(f"Found '{key}' key with {len(data[key])} items" if isinstance(data[key], list) else f"Found '{key}' key")
                
                return True, data
                
            except json.JSONDecodeError:
                print("Response is not valid JSON")
                print("Response text (first 200 chars):", response.text[:200])
        
        else:
            print(f"HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")
    
    return False, None


def main():
    """Main test function."""
    print("🔍 Josera API Endpoint Discovery Tool")
    print("=" * 50)
    
    # If you found the exact URL, add it here:
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        print(f"Testing provided URL: {test_url}")
        success, data = test_api_endpoint(test_url)
        if success:
            print("\n✅ Success! This endpoint works.")
            return
    
    # Common API endpoints to test
    base_url = "https://fachhandel.josera.de"
    
    endpoints_to_test = [
        "/api/stores",
        "/api/dealers",
        "/api/partners", 
        "/api/fachhandel",
        "/wp-json/wp/v2/stores",
        "/wp-json/stores",
        "/stores.json",
        "/dealers.json",
        "/api/v1/stores",
        "/wp-content/themes/josera/api/stores",
        "/data/stores.json",
        # Add more based on what you see in browser dev tools
    ]
    
    print(f"\nTesting {len(endpoints_to_test)} common endpoints...")
    
    for endpoint in endpoints_to_test:
        url = urljoin(base_url, endpoint)
        success, data = test_api_endpoint(url)
        
        if success:
            print(f"\n✅ FOUND WORKING ENDPOINT: {url}")
            print("=" * 50)
            break
        
        print("-" * 30)
    
    else:
        print("\n❌ No working endpoints found.")
        print("\nPlease check the browser dev tools Network tab and look for:")
        print("1. XHR/Fetch requests when the page loads")
        print("2. Requests that return JSON data")
        print("3. URLs containing 'store', 'dealer', or 'partner'")
        print("\nThen run: python test_josera_api.py <exact_url>")


if __name__ == "__main__":
    main() 