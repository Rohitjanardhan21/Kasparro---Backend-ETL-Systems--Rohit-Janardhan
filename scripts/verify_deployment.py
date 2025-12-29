#!/usr/bin/env python3
"""
Deployment Verification Script
Verifies that the deployed system is accessible and functional.
"""

import requests
import json
import sys
import time
from datetime import datetime

def test_endpoint(url, endpoint_name, expected_keys=None):
    """Test a single endpoint and verify response."""
    try:
        print(f"Testing {endpoint_name}: {url}")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {endpoint_name}: SUCCESS (Status: {response.status_code})")
            
            if expected_keys:
                missing_keys = [key for key in expected_keys if key not in data]
                if missing_keys:
                    print(f"⚠️  Missing keys: {missing_keys}")
                else:
                    print(f"✅ All expected keys present: {expected_keys}")
            
            print(f"   Response time: {response.elapsed.total_seconds():.3f}s")
            return True
        else:
            print(f"❌ {endpoint_name}: FAILED (Status: {response.status_code})")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ {endpoint_name}: ERROR - {str(e)}")
        return False

def verify_deployment(base_url):
    """Verify complete deployment functionality."""
    print(f"\n🔍 VERIFYING DEPLOYMENT: {base_url}")
    print("=" * 60)
    
    results = {}
    
    # Test health endpoint
    results['health'] = test_endpoint(
        f"{base_url}/health",
        "Health Check",
        ["status", "database_connected", "etl_last_run"]
    )
    
    # Test data endpoint
    results['data'] = test_endpoint(
        f"{base_url}/data?limit=3",
        "Data Endpoint",
        ["data", "pagination", "metadata"]
    )
    
    # Test stats endpoint
    results['stats'] = test_endpoint(
        f"{base_url}/stats",
        "Stats Endpoint",
        ["total_runs", "successful_runs", "records_by_source"]
    )
    
    # Test API documentation (HTML endpoint)
    try:
        print(f"Testing API Documentation: {base_url}/docs")
        response = requests.get(f"{base_url}/docs", timeout=10)
        if response.status_code == 200 and "swagger" in response.text.lower():
            print(f"✅ API Documentation: SUCCESS (Status: {response.status_code})")
            results['docs'] = True
        else:
            print(f"❌ API Documentation: FAILED (Status: {response.status_code})")
            results['docs'] = False
    except Exception as e:
        print(f"❌ API Documentation: ERROR - {str(e)}")
        results['docs'] = False
    
    print("\n📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for endpoint, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{endpoint.upper():<15}: {status}")
    
    print(f"\nOVERALL RESULT: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 DEPLOYMENT VERIFICATION: SUCCESS")
        return True
    else:
        print("💥 DEPLOYMENT VERIFICATION: FAILED")
        return False

def main():
    """Main verification function."""
    # Test multiple deployment URLs
    deployments = [
        "http://98.81.97.104",  # AWS EC2
        "http://localhost:8080",  # Local development
    ]
    
    print(f"🚀 KASPARRO ETL SYSTEM - DEPLOYMENT VERIFICATION")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    all_passed = True
    
    for base_url in deployments:
        success = verify_deployment(base_url)
        if not success:
            all_passed = False
        print()  # Add spacing between deployments
    
    if all_passed:
        print("🎯 ALL DEPLOYMENTS VERIFIED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("⚠️  SOME DEPLOYMENTS FAILED VERIFICATION")
        sys.exit(1)

if __name__ == "__main__":
    main()