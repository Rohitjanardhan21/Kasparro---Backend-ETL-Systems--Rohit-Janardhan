#!/usr/bin/env python3
"""
Quick test script to verify the system is working end-to-end.
This can be run after 'make up' to verify everything is functioning.
"""

import requests
import time
import json
import sys


def test_api_health():
    """Test the health endpoint."""
    print("🏥 Testing health endpoint...")
    
    try:
        response = requests.get("http://localhost:8001/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check: {data.get('status', 'unknown')}")
            print(f"   Database connected: {data.get('database_connected', False)}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health check exception: {str(e)}")
        return False


def test_data_endpoint():
    """Test the data endpoint."""
    print("\n📊 Testing data endpoint...")
    
    try:
        response = requests.get("http://localhost:8001/data?limit=5", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            record_count = len(data.get("data", []))
            total_records = data.get("pagination", {}).get("total_records", 0)
            
            print(f"✅ Data endpoint: Retrieved {record_count} records")
            print(f"   Total records in database: {total_records}")
            
            if record_count > 0:
                sample = data["data"][0]
                print(f"   Sample: {sample.get('name')} ({sample.get('symbol')}) - ${sample.get('price_usd', 'N/A')}")
            
            return True
        else:
            print(f"❌ Data endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Data endpoint exception: {str(e)}")
        return False


def test_stats_endpoint():
    """Test the stats endpoint."""
    print("\n📈 Testing stats endpoint...")
    
    try:
        response = requests.get("http://localhost:8001/stats", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            total_runs = data.get("total_runs", 0)
            successful_runs = data.get("successful_runs", 0)
            
            print(f"✅ Stats endpoint: {total_runs} total runs, {successful_runs} successful")
            
            records_by_source = data.get("records_by_source", {})
            for source, count in records_by_source.items():
                print(f"   {source}: {count} records")
            
            return True
        else:
            print(f"❌ Stats endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Stats endpoint exception: {str(e)}")
        return False


def test_api_docs():
    """Test that API documentation is accessible."""
    print("\n📚 Testing API documentation...")
    
    try:
        response = requests.get("http://localhost:8001/docs", timeout=10)
        
        if response.status_code == 200:
            print("✅ API docs accessible at http://localhost:8000/docs")
            return True
        else:
            print(f"❌ API docs failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ API docs exception: {str(e)}")
        return False


def wait_for_system():
    """Wait for the system to be ready."""
    print("⏳ Waiting for system to be ready...")
    
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get("http://localhost:8001/health", timeout=5)
            if response.status_code == 200:
                print("✅ System is ready!")
                return True
        except:
            pass
        
        print(f"   Attempt {attempt + 1}/{max_attempts}...")
        time.sleep(2)
    
    print("❌ System did not become ready in time")
    return False


def main():
    """Main test function."""
    print("🚀 Kasparro ETL System - Quick Test")
    print("=" * 50)
    
    # Wait for system to be ready
    if not wait_for_system():
        print("\n❌ System is not responding. Make sure you ran 'make up' first.")
        return False
    
    # Run tests
    tests = [
        ("Health Check", test_api_health),
        ("Data Endpoint", test_data_endpoint),
        ("Stats Endpoint", test_stats_endpoint),
        ("API Documentation", test_api_docs),
    ]
    
    results = []
    for test_name, test_func in tests:
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Your system is working correctly.")
        print("\n🔗 Useful URLs:")
        print("   • API Health: http://localhost:8001/health")
        print("   • Data API: http://localhost:8001/data")
        print("   • Statistics: http://localhost:8001/stats")
        print("   • API Docs: http://localhost:8001/docs")
        print("   • Alternative Docs: http://localhost:8001/redoc")
    else:
        print("\n⚠️  Some tests failed. Check the logs with 'make logs'")
    
    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)