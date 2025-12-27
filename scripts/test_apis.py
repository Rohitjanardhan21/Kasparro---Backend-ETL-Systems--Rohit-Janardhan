#!/usr/bin/env python3
"""
Test script to verify API integrations work correctly.
This script tests the actual API endpoints without requiring database setup.
"""

import requests
import json
import os
from typing import Dict, Any, Optional


def test_coinpaprika_api(api_key: Optional[str] = None) -> Dict[str, Any]:
    """Test CoinPaprika API integration."""
    print("🪙 Testing CoinPaprika API...")
    
    url = "https://api.coinpaprika.com/v1/tickers"
    headers = {"Accept": "application/json"}
    
    # Add API key if provided (for Pro features)
    if api_key and api_key != "your_coinpaprika_api_key_here":
        headers["Authorization"] = f"Bearer {api_key}"
    
    try:
        response = requests.get(url, headers=headers, params={"limit": 10}, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ CoinPaprika API: Success! Retrieved {len(data)} coins")
            
            # Show sample data structure
            if data:
                sample = data[0]
                print(f"   Sample coin: {sample.get('name')} ({sample.get('symbol')})")
                print(f"   Price: ${sample.get('quotes', {}).get('USD', {}).get('price', 'N/A')}")
                print(f"   Rank: {sample.get('rank', 'N/A')}")
            
            return {"status": "success", "count": len(data), "sample": data[0] if data else None}
        else:
            print(f"❌ CoinPaprika API: Error {response.status_code} - {response.text}")
            return {"status": "error", "code": response.status_code, "message": response.text}
            
    except Exception as e:
        print(f"❌ CoinPaprika API: Exception - {str(e)}")
        return {"status": "exception", "error": str(e)}


def test_coingecko_api(api_key: Optional[str] = None) -> Dict[str, Any]:
    """Test CoinGecko API integration."""
    print("\n🦎 Testing CoinGecko API...")
    
    url = "https://api.coingecko.com/api/v3/coins/markets"
    headers = {"Accept": "application/json"}
    
    # Add API key if provided (for Pro features)
    if api_key and api_key != "your_coingecko_api_key_here":
        headers["Authorization"] = f"Bearer {api_key}"
    
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 10,
        "page": 1,
        "sparkline": False
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ CoinGecko API: Success! Retrieved {len(data)} coins")
            
            # Show sample data structure
            if data:
                sample = data[0]
                print(f"   Sample coin: {sample.get('name')} ({sample.get('symbol', '').upper()})")
                print(f"   Price: ${sample.get('current_price', 'N/A')}")
                print(f"   Market Cap Rank: {sample.get('market_cap_rank', 'N/A')}")
            
            return {"status": "success", "count": len(data), "sample": data[0] if data else None}
        else:
            print(f"❌ CoinGecko API: Error {response.status_code} - {response.text}")
            return {"status": "error", "code": response.status_code, "message": response.text}
            
    except Exception as e:
        print(f"❌ CoinGecko API: Exception - {str(e)}")
        return {"status": "exception", "error": str(e)}


def test_rate_limits():
    """Test rate limiting behavior."""
    print("\n⏱️  Testing rate limits...")
    
    # Test CoinGecko rate limits (free tier: 10-50 calls/minute)
    print("Testing CoinGecko rate limits (making 5 quick requests)...")
    
    for i in range(5):
        try:
            response = requests.get(
                "https://api.coingecko.com/api/v3/ping",
                timeout=10
            )
            if response.status_code == 200:
                print(f"   Request {i+1}: ✅ Success")
            elif response.status_code == 429:
                print(f"   Request {i+1}: ⚠️  Rate limited")
                break
            else:
                print(f"   Request {i+1}: ❌ Error {response.status_code}")
        except Exception as e:
            print(f"   Request {i+1}: ❌ Exception - {str(e)}")


def main():
    """Main test function."""
    print("🚀 API Integration Test Suite")
    print("=" * 50)
    
    # Get API keys from environment
    coinpaprika_key = os.getenv("COINPAPRIKA_API_KEY")
    coingecko_key = os.getenv("COINGECKO_API_KEY")
    
    if not coinpaprika_key or coinpaprika_key == "your_coinpaprika_api_key_here":
        print("⚠️  No CoinPaprika API key found - testing with free tier")
        coinpaprika_key = None
    
    if not coingecko_key or coingecko_key == "your_coingecko_api_key_here":
        print("⚠️  No CoinGecko API key found - testing with free tier")
        coingecko_key = None
    
    # Test APIs
    coinpaprika_result = test_coinpaprika_api(coinpaprika_key)
    coingecko_result = test_coingecko_api(coingecko_key)
    
    # Test rate limits
    test_rate_limits()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"   CoinPaprika: {'✅ PASS' if coinpaprika_result['status'] == 'success' else '❌ FAIL'}")
    print(f"   CoinGecko: {'✅ PASS' if coingecko_result['status'] == 'success' else '❌ FAIL'}")
    
    # API Usage Notes
    print("\n📝 API Usage Notes:")
    print("   • CoinPaprika: Free tier allows unlimited requests")
    print("   • CoinGecko: Free tier allows 10-50 calls/minute")
    print("   • Both APIs work without API keys for basic functionality")
    print("   • API keys provide higher rate limits and additional features")
    
    # Save test results
    results = {
        "coinpaprika": coinpaprika_result,
        "coingecko": coingecko_result,
        "timestamp": "2024-01-01T00:00:00Z"  # Would be datetime.utcnow().isoformat() in real usage
    }
    
    with open("api_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Test results saved to: api_test_results.json")
    
    # Return success if both APIs work
    return (coinpaprika_result["status"] == "success" and 
            coingecko_result["status"] == "success")


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)