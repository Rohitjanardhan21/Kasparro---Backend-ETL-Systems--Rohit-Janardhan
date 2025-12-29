#!/usr/bin/env python3
"""
Security Audit for Kasparro ETL System
Tests for common security vulnerabilities
"""

import requests
import json
import time
from datetime import datetime

class SecurityAudit:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.vulnerabilities = []
        self.security_score = 0
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def test_sql_injection(self):
        """Test for SQL injection vulnerabilities"""
        self.log("🔍 Testing SQL Injection Protection")
        
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM information_schema.tables --",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --",
            "' OR 1=1 --",
            "admin'--",
            "admin' /*",
            "' OR 'x'='x",
            "1' AND 1=1 --",
            "' AND (SELECT COUNT(*) FROM users) > 0 --"
        ]
        
        vulnerable_endpoints = []
        
        for payload in sql_payloads:
            params = {
                "coin_id": payload,
                "symbol": payload,
                "source": payload
            }
            
            try:
                response = requests.get(f"{self.base_url}/data", params=params, timeout=10)
                
                # Check for SQL error messages
                response_text = response.text.lower()
                sql_errors = [
                    "sql syntax", "mysql", "postgresql", "sqlite", "oracle",
                    "syntax error", "database error", "column", "table",
                    "constraint", "foreign key", "primary key"
                ]
                
                if any(error in response_text for error in sql_errors):
                    vulnerable_endpoints.append({
                        "payload": payload,
                        "response_code": response.status_code,
                        "vulnerability": "SQL error exposed"
                    })
                    self.log(f"   ⚠️  SQL Error exposed with payload: {payload[:30]}...")
                elif response.status_code == 200:
                    # Check if payload was processed (potential injection)
                    data = response.json()
                    if len(data.get("data", [])) > 1000:  # Unusually large result
                        vulnerable_endpoints.append({
                            "payload": payload,
                            "response_code": response.status_code,
                            "vulnerability": "Potential SQL injection"
                        })
                        self.log(f"   ⚠️  Potential injection with payload: {payload[:30]}...")
                else:
                    self.log(f"   ✅ Payload rejected: {payload[:30]}...")
                    
            except Exception as e:
                self.log(f"   💥 Error testing payload {payload[:20]}: {str(e)[:50]}")
        
        if not vulnerable_endpoints:
            self.log("   ✅ No SQL injection vulnerabilities found")
            self.security_score += 20
        else:
            self.vulnerabilities.extend(vulnerable_endpoints)
    
    def test_xss_protection(self):
        """Test for XSS vulnerabilities"""
        self.log("🔍 Testing XSS Protection")
        
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "<img src=x onerror=alert(1)>",
            "<svg onload=alert(1)>",
            "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//",
            "\"><script>alert('XSS')</script>",
            "<iframe src=javascript:alert(1)></iframe>",
            "<body onload=alert(1)>",
            "<input onfocus=alert(1) autofocus>",
            "<select onfocus=alert(1) autofocus>"
        ]
        
        xss_vulnerabilities = []
        
        for payload in xss_payloads:
            params = {"coin_id": payload, "symbol": payload}
            
            try:
                response = requests.get(f"{self.base_url}/data", params=params, timeout=10)
                
                if payload in response.text and response.headers.get('content-type', '').startswith('text/html'):
                    xss_vulnerabilities.append({
                        "payload": payload,
                        "vulnerability": "XSS payload reflected in HTML response"
                    })
                    self.log(f"   ⚠️  XSS vulnerability: {payload[:30]}...")
                else:
                    self.log(f"   ✅ XSS payload handled: {payload[:30]}...")
                    
            except Exception as e:
                self.log(f"   💥 Error testing XSS: {str(e)[:50]}")
        
        if not xss_vulnerabilities:
            self.log("   ✅ No XSS vulnerabilities found")
            self.security_score += 15
        else:
            self.vulnerabilities.extend(xss_vulnerabilities)
    
    def test_path_traversal(self):
        """Test for path traversal vulnerabilities"""
        self.log("🔍 Testing Path Traversal Protection")
        
        path_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd"
        ]
        
        path_vulnerabilities = []
        
        for payload in path_payloads:
            try:
                # Test different endpoints
                endpoints = [f"/data/{payload}", f"/{payload}", f"/health/{payload}"]
                
                for endpoint in endpoints:
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                    
                    # Check for file content indicators
                    response_text = response.text.lower()
                    file_indicators = ["root:", "bin/bash", "system32", "windows", "[users]"]
                    
                    if any(indicator in response_text for indicator in file_indicators):
                        path_vulnerabilities.append({
                            "payload": payload,
                            "endpoint": endpoint,
                            "vulnerability": "Path traversal successful"
                        })
                        self.log(f"   ⚠️  Path traversal: {payload}")
                        break
                else:
                    self.log(f"   ✅ Path traversal blocked: {payload}")
                    
            except Exception as e:
                self.log(f"   💥 Error testing path traversal: {str(e)[:50]}")
        
        if not path_vulnerabilities:
            self.log("   ✅ No path traversal vulnerabilities found")
            self.security_score += 15
        else:
            self.vulnerabilities.extend(path_vulnerabilities)
    
    def test_http_headers(self):
        """Test security headers"""
        self.log("🔍 Testing Security Headers")
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            headers = response.headers
            
            security_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": ["DENY", "SAMEORIGIN"],
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": "max-age=",
                "Content-Security-Policy": "default-src",
                "Referrer-Policy": ["no-referrer", "strict-origin"]
            }
            
            header_score = 0
            missing_headers = []
            
            for header, expected in security_headers.items():
                if header in headers:
                    if isinstance(expected, list):
                        if any(exp in headers[header] for exp in expected):
                            header_score += 1
                            self.log(f"   ✅ {header}: {headers[header]}")
                        else:
                            missing_headers.append(header)
                            self.log(f"   ⚠️  {header}: Weak value")
                    else:
                        if expected in headers[header]:
                            header_score += 1
                            self.log(f"   ✅ {header}: {headers[header]}")
                        else:
                            missing_headers.append(header)
                            self.log(f"   ⚠️  {header}: Weak value")
                else:
                    missing_headers.append(header)
                    self.log(f"   ❌ Missing: {header}")
            
            self.security_score += (header_score / len(security_headers)) * 20
            
            if missing_headers:
                self.vulnerabilities.append({
                    "vulnerability": "Missing security headers",
                    "missing_headers": missing_headers
                })
                
        except Exception as e:
            self.log(f"   💥 Error testing headers: {str(e)[:50]}")
    
    def test_rate_limiting(self):
        """Test rate limiting implementation"""
        self.log("🔍 Testing Rate Limiting")
        
        try:
            # Make rapid requests to test rate limiting
            start_time = time.time()
            responses = []
            
            for i in range(50):
                response = requests.get(f"{self.base_url}/data?limit=1", timeout=5)
                responses.append(response.status_code)
                
                if response.status_code == 429:  # Too Many Requests
                    self.log(f"   ✅ Rate limiting active after {i+1} requests")
                    self.security_score += 10
                    return
                elif response.status_code != 200:
                    break
            
            total_time = time.time() - start_time
            rps = len(responses) / total_time
            
            if rps > 100:  # Very high RPS might indicate no rate limiting
                self.log(f"   ⚠️  High RPS ({rps:.1f}) - Rate limiting may be insufficient")
                self.vulnerabilities.append({
                    "vulnerability": "Insufficient rate limiting",
                    "rps_achieved": rps
                })
            else:
                self.log(f"   ✅ Reasonable RPS ({rps:.1f}) - Rate limiting appears adequate")
                self.security_score += 5
                
        except Exception as e:
            self.log(f"   💥 Error testing rate limiting: {str(e)[:50]}")
    
    def test_information_disclosure(self):
        """Test for information disclosure"""
        self.log("🔍 Testing Information Disclosure")
        
        sensitive_endpoints = [
            "/.env",
            "/config",
            "/admin",
            "/debug",
            "/test",
            "/backup",
            "/logs",
            "/status",
            "/info",
            "/version"
        ]
        
        disclosed_info = []
        
        for endpoint in sensitive_endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                
                if response.status_code == 200:
                    # Check for sensitive information
                    response_text = response.text.lower()
                    sensitive_patterns = [
                        "password", "secret", "key", "token", "database_url",
                        "api_key", "private", "config", "debug", "stack trace"
                    ]
                    
                    found_sensitive = [p for p in sensitive_patterns if p in response_text]
                    
                    if found_sensitive:
                        disclosed_info.append({
                            "endpoint": endpoint,
                            "status_code": response.status_code,
                            "sensitive_data": found_sensitive
                        })
                        self.log(f"   ⚠️  Information disclosed at {endpoint}: {found_sensitive}")
                    else:
                        self.log(f"   ⚠️  Accessible endpoint: {endpoint} (no sensitive data)")
                else:
                    self.log(f"   ✅ Endpoint protected: {endpoint}")
                    
            except Exception as e:
                self.log(f"   💥 Error testing {endpoint}: {str(e)[:50]}")
        
        if not disclosed_info:
            self.log("   ✅ No information disclosure found")
            self.security_score += 20
        else:
            self.vulnerabilities.extend(disclosed_info)
    
    def run_security_audit(self):
        """Run complete security audit"""
        self.log("🛡️  STARTING SECURITY AUDIT", "START")
        start_time = time.time()
        
        try:
            # Test connectivity first
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code != 200:
                self.log("❌ System not accessible for security testing", "ERROR")
                return
            
            # Run all security tests
            self.test_sql_injection()
            self.test_xss_protection()
            self.test_path_traversal()
            self.test_http_headers()
            self.test_rate_limiting()
            self.test_information_disclosure()
            
        except Exception as e:
            self.log(f"💥 CRITICAL ERROR: {str(e)}", "ERROR")
        
        total_time = time.time() - start_time
        self.log(f"🏁 SECURITY AUDIT COMPLETE in {total_time:.1f}s", "COMPLETE")
        
        # Generate security report
        self.generate_security_report()
    
    def generate_security_report(self):
        """Generate security audit report"""
        print("\n" + "="*80)
        print("🛡️  SECURITY AUDIT REPORT")
        print("="*80)
        
        print(f"\n📊 SECURITY SCORE: {self.security_score:.1f}/100")
        
        if self.security_score >= 90:
            grade = "🏆 EXCELLENT"
            color = "🟢"
        elif self.security_score >= 75:
            grade = "🥇 GOOD"
            color = "🟡"
        elif self.security_score >= 60:
            grade = "🥈 ACCEPTABLE"
            color = "🟠"
        else:
            grade = "❌ NEEDS IMPROVEMENT"
            color = "🔴"
        
        print(f"📈 SECURITY GRADE: {color} {grade}")
        
        if self.vulnerabilities:
            print(f"\n⚠️  VULNERABILITIES FOUND ({len(self.vulnerabilities)}):")
            for i, vuln in enumerate(self.vulnerabilities, 1):
                print(f"   {i}. {vuln.get('vulnerability', 'Unknown vulnerability')}")
                if 'payload' in vuln:
                    print(f"      Payload: {vuln['payload'][:50]}...")
                if 'endpoint' in vuln:
                    print(f"      Endpoint: {vuln['endpoint']}")
        else:
            print("\n✅ NO CRITICAL VULNERABILITIES FOUND")
        
        print(f"\n🎯 SECURITY RECOMMENDATIONS:")
        if self.security_score < 90:
            print("   • Implement additional input validation")
            print("   • Add security headers (CSP, HSTS, etc.)")
            print("   • Implement rate limiting")
            print("   • Review error handling to prevent information disclosure")
        else:
            print("   • Security posture is strong")
            print("   • Continue monitoring and regular security audits")
        
        print("\n" + "="*80)

if __name__ == "__main__":
    # Test both local and cloud deployments
    test_urls = [
        "http://localhost:8080",
        "http://98.81.97.104"
    ]
    
    for url in test_urls:
        print(f"\n🎯 Security Testing: {url}")
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                auditor = SecurityAudit(url)
                auditor.run_security_audit()
            else:
                print(f"❌ {url} not accessible")
        except Exception as e:
            print(f"❌ {url} failed: {str(e)[:50]}")