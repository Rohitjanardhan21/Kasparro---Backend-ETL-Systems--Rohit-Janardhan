#!/usr/bin/env python3
"""
Final verification script to demonstrate system readiness for deployment.
This script performs comprehensive end-to-end testing.
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any


def test_api_endpoint(url: str, endpoint: str) -> Dict[str, Any]:
    """Test a specific API endpoint."""
    try:
        response = requests.get(f"{url}{endpoint}", timeout=10)
        return {
            "status": "success" if response.status_code == 200 else "error",
            "status_code": response.status_code,
            "response_time_ms": response.elapsed.total_seconds() * 1000,
            "data": response.json() if response.status_code == 200 else response.text
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def main():
    """Run comprehensive system verification."""
    print("🎯 Kasparro ETL System - Final Verification")
    print("=" * 60)
    
    # System configuration
    api_url = "http://localhost:8001"
    
    print(f"🔍 Testing API at: {api_url}")
    print(f"⏰ Test time: {datetime.now().isoformat()}")
    print()
    
    # Test all endpoints
    endpoints = [
        ("/health", "Health Check"),
        ("/data?limit=5", "Data Endpoint (5 records)"),
        ("/data?source=csv&limit=3", "CSV Data Filter"),
        ("/data?source=coinpaprika&limit=3", "CoinPaprika Data Filter"),
        ("/data?source=coingecko&limit=3", "CoinGecko Data Filter"),
        ("/stats", "ETL Statistics")
    ]
    
    results = {}
    all_passed = True
    
    for endpoint, description in endpoints:
        print(f"🧪 Testing {description}...")
        result = test_api_endpoint(api_url, endpoint)
        results[endpoint] = result
        
        if result["status"] == "success":
            print(f"   ✅ SUCCESS - {result['response_time_ms']:.1f}ms")
            
            # Show sample data for data endpoints
            if endpoint.startswith("/data"):
                data = result["data"]
                if "data" in data and data["data"]:
                    sample = data["data"][0]
                    print(f"      Sample: {sample.get('name', 'N/A')} ({sample.get('symbol', 'N/A')}) - ${sample.get('price_usd', 'N/A')}")
                    print(f"      Total records: {data.get('pagination', {}).get('total_records', 'N/A')}")
            
            elif endpoint == "/stats":
                stats = result["data"]
                print(f"      Total ETL runs: {stats.get('total_runs', 'N/A')}")
                print(f"      Records by source: {stats.get('records_by_source', {})}")
                
            elif endpoint == "/health":
                health = result["data"]
                print(f"      Status: {health.get('status', 'N/A')}")
                print(f"      DB Connected: {health.get('database_connected', 'N/A')}")
        else:
            print(f"   ❌ FAILED - {result.get('error', result.get('status_code', 'Unknown error'))}")
            all_passed = False
        
        print()
    
    # Performance summary
    print("📊 Performance Summary:")
    response_times = [r["response_time_ms"] for r in results.values() if "response_time_ms" in r]
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        print(f"   Average response time: {avg_time:.1f}ms")
        print(f"   Maximum response time: {max_time:.1f}ms")
    print()
    
    # Data verification
    print("📈 Data Verification:")
    data_result = results.get("/data?limit=5", {})
    if data_result.get("status") == "success":
        data = data_result["data"]
        total_records = data.get("pagination", {}).get("total_records", 0)
        print(f"   Total records in database: {total_records}")
        
        # Check data sources
        sources = set()
        for record in data.get("data", []):
            sources.add(record.get("source", "unknown"))
        print(f"   Data sources active: {', '.join(sorted(sources))}")
    print()
    
    # System readiness assessment
    print("🎯 System Readiness Assessment:")
    print("=" * 40)
    
    readiness_checks = [
        ("API Health", results.get("/health", {}).get("status") == "success"),
        ("Data Retrieval", results.get("/data?limit=5", {}).get("status") == "success"),
        ("Multi-source Data", len([r for r in results.values() if r.get("status") == "success" and "source=" in str(r)]) >= 3),
        ("Statistics Endpoint", results.get("/stats", {}).get("status") == "success"),
        ("Response Performance", avg_time < 1000 if response_times else False),
    ]
    
    for check_name, passed in readiness_checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {check_name}: {status}")
    
    overall_ready = all(passed for _, passed in readiness_checks)
    
    print()
    print("🚀 DEPLOYMENT READINESS:")
    if overall_ready:
        print("   🎉 SYSTEM IS READY FOR CLOUD DEPLOYMENT!")
        print("   📋 All core functionality verified")
        print("   🔧 APIs working with real data")
        print("   ⚡ Performance within acceptable limits")
        print()
        print("   Next steps:")
        print("   1. Run: ./deploy/aws-deploy.sh (or gcp-deploy.sh)")
        print("   2. Verify cloud endpoints")
        print("   3. Test automated ETL scheduling")
        print("   4. Complete assignment submission")
    else:
        print("   ⚠️  SYSTEM NEEDS ATTENTION BEFORE DEPLOYMENT")
        print("   🔧 Fix failing checks above")
        print("   🔄 Re-run verification")
    
    print()
    print("=" * 60)
    
    # Save results
    verification_report = {
        "timestamp": datetime.now().isoformat(),
        "api_url": api_url,
        "endpoint_results": results,
        "readiness_checks": dict(readiness_checks),
        "overall_ready": overall_ready,
        "performance": {
            "avg_response_time_ms": avg_time if response_times else None,
            "max_response_time_ms": max_time if response_times else None
        }
    }
    
    with open("verification_report.json", "w") as f:
        json.dump(verification_report, f, indent=2)
    
    print(f"📄 Verification report saved: verification_report.json")
    
    return overall_ready


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)