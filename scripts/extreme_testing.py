#!/usr/bin/env python3
"""
Extreme Testing Suite for Kasparro ETL System
Tests system under stress, edge cases, and failure scenarios
"""

import asyncio
import aiohttp
import requests
import time
import json
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import psutil
import os

class ExtremeTestSuite:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.results = {
            "load_test": {},
            "stress_test": {},
            "edge_cases": {},
            "failure_scenarios": {},
            "performance": {},
            "security": {}
        }
        
    def log(self, message, test_type="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {test_type}: {message}")
    
    def test_api_load(self, concurrent_requests=50, total_requests=1000):
        """Test API under heavy concurrent load"""
        self.log(f"🔥 LOAD TEST: {concurrent_requests} concurrent, {total_requests} total requests")
        
        start_time = time.time()
        success_count = 0
        error_count = 0
        response_times = []
        
        def make_request(endpoint):
            try:
                req_start = time.time()
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                req_time = time.time() - req_start
                response_times.append(req_time)
                
                if response.status_code == 200:
                    return "success"
                else:
                    return f"error_{response.status_code}"
            except Exception as e:
                return f"exception_{str(e)[:50]}"
        
        # Test different endpoints
        endpoints = ["/health", "/data?limit=10", "/stats", "/data?page=1&limit=5"]
        
        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            futures = []
            for i in range(total_requests):
                endpoint = random.choice(endpoints)
                futures.append(executor.submit(make_request, endpoint))
            
            for future in as_completed(futures):
                result = future.result()
                if result == "success":
                    success_count += 1
                else:
                    error_count += 1
        
        total_time = time.time() - start_time
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        requests_per_second = total_requests / total_time
        
        self.results["load_test"] = {
            "total_requests": total_requests,
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": (success_count / total_requests) * 100,
            "total_time": total_time,
            "requests_per_second": requests_per_second,
            "avg_response_time": avg_response_time,
            "max_response_time": max(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0
        }
        
        self.log(f"✅ LOAD TEST COMPLETE: {success_count}/{total_requests} success ({(success_count/total_requests)*100:.1f}%)")
        self.log(f"   RPS: {requests_per_second:.1f}, Avg Response: {avg_response_time*1000:.1f}ms")
    
    def test_data_pagination_stress(self):
        """Test pagination with extreme parameters"""
        self.log("🔥 PAGINATION STRESS TEST")
        
        test_cases = [
            {"page": 1, "limit": 1},      # Minimum
            {"page": 1, "limit": 1000},   # Maximum
            {"page": 100, "limit": 50},   # High page number
            {"page": 1000, "limit": 1},   # Very high page
            {"page": 1, "limit": 999},    # Near maximum
        ]
        
        results = []
        for case in test_cases:
            try:
                start_time = time.time()
                response = requests.get(
                    f"{self.base_url}/data",
                    params=case,
                    timeout=30
                )
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    results.append({
                        "case": case,
                        "status": "success",
                        "response_time": response_time,
                        "records_returned": len(data.get("data", [])),
                        "total_records": data.get("pagination", {}).get("total_records", 0)
                    })
                    self.log(f"   ✅ Page {case['page']}, Limit {case['limit']}: {response_time*1000:.1f}ms")
                else:
                    results.append({
                        "case": case,
                        "status": f"error_{response.status_code}",
                        "response_time": response_time
                    })
                    self.log(f"   ❌ Page {case['page']}, Limit {case['limit']}: HTTP {response.status_code}")
                    
            except Exception as e:
                results.append({
                    "case": case,
                    "status": f"exception_{str(e)[:50]}",
                    "response_time": None
                })
                self.log(f"   💥 Page {case['page']}, Limit {case['limit']}: {str(e)[:50]}")
        
        self.results["stress_test"]["pagination"] = results
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        self.log("🔥 EDGE CASE TESTING")
        
        edge_cases = [
            # Invalid parameters
            {"endpoint": "/data", "params": {"page": 0}},
            {"endpoint": "/data", "params": {"page": -1}},
            {"endpoint": "/data", "params": {"limit": 0}},
            {"endpoint": "/data", "params": {"limit": -1}},
            {"endpoint": "/data", "params": {"limit": 10000}},
            {"endpoint": "/data", "params": {"source": "invalid_source"}},
            {"endpoint": "/data", "params": {"coin_id": ""}},
            {"endpoint": "/data", "params": {"symbol": "NONEXISTENT"}},
            
            # SQL injection attempts
            {"endpoint": "/data", "params": {"coin_id": "'; DROP TABLE users; --"}},
            {"endpoint": "/data", "params": {"symbol": "' OR '1'='1"}},
            {"endpoint": "/data", "params": {"source": "csv'; SELECT * FROM raw_csv_data; --"}},
            
            # XSS attempts
            {"endpoint": "/data", "params": {"coin_id": "<script>alert('xss')</script>"}},
            {"endpoint": "/data", "params": {"symbol": "javascript:alert(1)"}},
            
            # Large payloads
            {"endpoint": "/data", "params": {"coin_id": "A" * 10000}},
            {"endpoint": "/data", "params": {"symbol": "B" * 1000}},
        ]
        
        results = []
        for case in edge_cases:
            try:
                response = requests.get(
                    f"{self.base_url}{case['endpoint']}",
                    params=case.get("params", {}),
                    timeout=10
                )
                
                results.append({
                    "case": case,
                    "status_code": response.status_code,
                    "response_size": len(response.content),
                    "handled_gracefully": response.status_code in [400, 422, 404]
                })
                
                if response.status_code in [400, 422, 404]:
                    self.log(f"   ✅ Edge case handled: {case['params']} -> HTTP {response.status_code}")
                elif response.status_code == 200:
                    self.log(f"   ⚠️  Edge case accepted: {case['params']} -> HTTP 200")
                else:
                    self.log(f"   ❌ Unexpected response: {case['params']} -> HTTP {response.status_code}")
                    
            except Exception as e:
                results.append({
                    "case": case,
                    "status_code": None,
                    "error": str(e)[:100],
                    "handled_gracefully": False
                })
                self.log(f"   💥 Exception: {case['params']} -> {str(e)[:50]}")
        
        self.results["edge_cases"] = results
    
    def test_concurrent_etl_runs(self):
        """Test multiple ETL processes running simultaneously"""
        self.log("🔥 CONCURRENT ETL TESTING")
        
        def run_etl():
            try:
                import subprocess
                result = subprocess.run(
                    ["docker-compose", "exec", "-T", "app", "python", "-m", "ingestion.main"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout[-500:],  # Last 500 chars
                    "stderr": result.stderr[-500:] if result.stderr else None
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # Run 3 ETL processes concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(run_etl) for _ in range(3)]
            etl_results = [future.result() for future in as_completed(futures)]
        
        success_count = sum(1 for r in etl_results if r.get("success", False))
        self.results["stress_test"]["concurrent_etl"] = {
            "total_runs": len(etl_results),
            "successful_runs": success_count,
            "results": etl_results
        }
        
        self.log(f"   ✅ Concurrent ETL: {success_count}/{len(etl_results)} successful")
    
    def test_memory_usage(self):
        """Monitor memory usage during operations"""
        self.log("🔥 MEMORY USAGE TESTING")
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Make many requests to test for memory leaks
        for i in range(100):
            try:
                requests.get(f"{self.base_url}/data?limit=100", timeout=5)
                if i % 20 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024
                    self.log(f"   Memory after {i} requests: {current_memory:.1f}MB")
            except:
                pass
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        self.results["performance"]["memory"] = {
            "initial_mb": initial_memory,
            "final_mb": final_memory,
            "increase_mb": memory_increase,
            "potential_leak": memory_increase > 50  # Flag if >50MB increase
        }
        
        self.log(f"   Memory usage: {initial_memory:.1f}MB -> {final_memory:.1f}MB (+{memory_increase:.1f}MB)")
    
    def test_database_stress(self):
        """Test database under stress"""
        self.log("🔥 DATABASE STRESS TESTING")
        
        # Test rapid consecutive requests
        start_time = time.time()
        consecutive_requests = 200
        success_count = 0
        
        for i in range(consecutive_requests):
            try:
                response = requests.get(f"{self.base_url}/data?limit=1", timeout=5)
                if response.status_code == 200:
                    success_count += 1
            except:
                pass
        
        total_time = time.time() - start_time
        
        self.results["stress_test"]["database"] = {
            "consecutive_requests": consecutive_requests,
            "successful_requests": success_count,
            "total_time": total_time,
            "requests_per_second": consecutive_requests / total_time,
            "success_rate": (success_count / consecutive_requests) * 100
        }
        
        self.log(f"   DB Stress: {success_count}/{consecutive_requests} success, {consecutive_requests/total_time:.1f} RPS")
    
    def test_error_recovery(self):
        """Test system recovery from various error conditions"""
        self.log("🔥 ERROR RECOVERY TESTING")
        
        # Test invalid endpoints
        invalid_endpoints = [
            "/nonexistent",
            "/data/../../../etc/passwd",
            "/admin",
            "/debug",
            "/.env",
            "/config"
        ]
        
        recovery_results = []
        for endpoint in invalid_endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                recovery_results.append({
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "handled_properly": response.status_code == 404
                })
            except Exception as e:
                recovery_results.append({
                    "endpoint": endpoint,
                    "error": str(e)[:50],
                    "handled_properly": False
                })
        
        # Test if system still works after error attempts
        try:
            health_response = requests.get(f"{self.base_url}/health", timeout=5)
            system_recovered = health_response.status_code == 200
        except:
            system_recovered = False
        
        self.results["failure_scenarios"]["error_recovery"] = {
            "invalid_endpoint_tests": recovery_results,
            "system_recovered": system_recovered
        }
        
        properly_handled = sum(1 for r in recovery_results if r.get("handled_properly", False))
        self.log(f"   Error Recovery: {properly_handled}/{len(recovery_results)} properly handled")
        self.log(f"   System Recovery: {'✅ YES' if system_recovered else '❌ NO'}")
    
    def run_all_tests(self):
        """Run the complete extreme testing suite"""
        self.log("🚀 STARTING EXTREME TESTING SUITE", "START")
        overall_start = time.time()
        
        try:
            # Basic connectivity test
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code != 200:
                self.log("❌ System not accessible, aborting tests", "ERROR")
                return
            
            # Run all test categories
            self.test_api_load(concurrent_requests=25, total_requests=500)
            self.test_data_pagination_stress()
            self.test_edge_cases()
            self.test_database_stress()
            self.test_error_recovery()
            # self.test_concurrent_etl_runs()  # Skip if too resource intensive
            # self.test_memory_usage()  # Skip if not needed
            
        except Exception as e:
            self.log(f"💥 CRITICAL ERROR: {str(e)}", "ERROR")
        
        total_time = time.time() - overall_start
        self.log(f"🏁 EXTREME TESTING COMPLETE in {total_time:.1f}s", "COMPLETE")
        
        # Generate summary report
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*80)
        print("🧪 EXTREME TESTING REPORT")
        print("="*80)
        
        # Load Test Results
        if "load_test" in self.results:
            lt = self.results["load_test"]
            print(f"\n📊 LOAD TEST RESULTS:")
            print(f"   Success Rate: {lt.get('success_rate', 0):.1f}%")
            print(f"   Requests/Second: {lt.get('requests_per_second', 0):.1f}")
            print(f"   Avg Response Time: {lt.get('avg_response_time', 0)*1000:.1f}ms")
            print(f"   Max Response Time: {lt.get('max_response_time', 0)*1000:.1f}ms")
        
        # Edge Cases
        if "edge_cases" in self.results:
            edge_results = self.results["edge_cases"]
            handled_properly = sum(1 for r in edge_results if r.get("handled_gracefully", False))
            print(f"\n🛡️  SECURITY & EDGE CASES:")
            print(f"   Properly Handled: {handled_properly}/{len(edge_results)}")
            print(f"   Security Score: {(handled_properly/len(edge_results))*100:.1f}%")
        
        # Database Stress
        if "stress_test" in self.results and "database" in self.results["stress_test"]:
            db = self.results["stress_test"]["database"]
            print(f"\n💾 DATABASE STRESS:")
            print(f"   Success Rate: {db.get('success_rate', 0):.1f}%")
            print(f"   Peak RPS: {db.get('requests_per_second', 0):.1f}")
        
        # Overall Assessment
        print(f"\n🎯 OVERALL ASSESSMENT:")
        
        # Calculate overall score
        scores = []
        if "load_test" in self.results:
            scores.append(min(self.results["load_test"].get("success_rate", 0), 100))
        if "edge_cases" in self.results:
            edge_score = (handled_properly/len(self.results["edge_cases"]))*100
            scores.append(edge_score)
        if "stress_test" in self.results and "database" in self.results["stress_test"]:
            scores.append(self.results["stress_test"]["database"].get("success_rate", 0))
        
        overall_score = sum(scores) / len(scores) if scores else 0
        
        if overall_score >= 95:
            grade = "🏆 EXCELLENT"
        elif overall_score >= 85:
            grade = "🥇 VERY GOOD"
        elif overall_score >= 75:
            grade = "🥈 GOOD"
        elif overall_score >= 65:
            grade = "🥉 ACCEPTABLE"
        else:
            grade = "❌ NEEDS IMPROVEMENT"
        
        print(f"   Overall Score: {overall_score:.1f}%")
        print(f"   Grade: {grade}")
        
        print("\n" + "="*80)

if __name__ == "__main__":
    # Test both local and cloud deployments
    test_urls = [
        "http://localhost:8080",
        "http://98.81.97.104"
    ]
    
    for url in test_urls:
        print(f"\n🎯 Testing: {url}")
        try:
            # Quick connectivity check
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                tester = ExtremeTestSuite(url)
                tester.run_all_tests()
            else:
                print(f"❌ {url} not accessible")
        except Exception as e:
            print(f"❌ {url} failed: {str(e)[:50]}")