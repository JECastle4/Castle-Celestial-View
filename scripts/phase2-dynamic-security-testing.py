#!/usr/bin/env python3
"""
Phase 2: Dynamic Security Testing for Castle Celestial View

Comprehensive API and infrastructure security testing including:
- API boundary and input validation testing
- CORS enforcement verification
- Error handling and information disclosure
- Security header validation
- TLS/SSL configuration testing
- XSS and injection attempt detection

Run: python3 scripts/phase2-dynamic-security-testing.py <target_url>
Example: python3 scripts/phase2-dynamic-security-testing.py https://castlecelestialview.net
"""

import sys
import json
import requests
import ssl
from urllib3.exceptions import InsecureRequestWarning
from datetime import datetime
from typing import Dict, List, Tuple

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class SecurityTester:
    def __init__(self, target_url: str):
        self.target = target_url.rstrip('/')
        self.api_base = f"{self.target}/api/v1"
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'target': self.target,
            'tests': []
        }
        self.session = requests.Session()
        self.session.verify = False
        
    def test(self, name: str, category: str, passed: bool, details: str = ""):
        """Record a test result"""
        result = {
            'name': name,
            'category': category,
            'passed': passed,
            'details': details
        }
        self.results['tests'].append(result)
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status:7} | {category:20} | {name:40} | {details}")
        return passed

    def print_section(self, title: str):
        """Print a test section header"""
        print(f"\n{'='*120}")
        print(f"  {title}")
        print(f"{'='*120}\n")

    # ─── API Boundary Testing ──────────────────────────────────────────────────
    
    def test_api_latitude_bounds(self):
        """Test latitude boundary validation"""
        self.print_section("1. API BOUNDARY TESTING: Latitude Validation")
        
        test_cases = [
            (-90, "min_valid", True),
            (-91, "min_invalid", False),
            (90, "max_valid", True),
            (91, "max_invalid", False),
            (0, "equator", True),
        ]
        
        for lat, desc, should_pass in test_cases:
            try:
                r = self.session.post(
                    f"{self.api_base}/sun-position",
                    json={"latitude": lat, "longitude": 0, "date": "2026-08-01", "time": "12:00:00"},
                    timeout=5
                )
                if should_pass:
                    passed = r.status_code == 200
                    self.test(f"latitude={lat}", "Boundary", passed, f"Status: {r.status_code}")
                else:
                    passed = r.status_code == 422  # Validation error expected
                    self.test(f"latitude={lat}", "Boundary", passed, f"Status: {r.status_code} (expected 422)")
            except Exception as e:
                self.test(f"latitude={lat}", "Boundary", False, str(e)[:50])

    def test_api_longitude_bounds(self):
        """Test longitude boundary validation"""
        self.print_section("2. API BOUNDARY TESTING: Longitude Validation")
        
        test_cases = [
            (-180, "min_valid", True),
            (-181, "min_invalid", False),
            (180, "max_valid", True),
            (181, "max_invalid", False),
            (0, "prime_meridian", True),
        ]
        
        for lon, desc, should_pass in test_cases:
            try:
                r = self.session.post(
                    f"{self.api_base}/sun-position",
                    json={"latitude": 0, "longitude": lon, "date": "2026-08-01", "time": "12:00:00"},
                    timeout=5
                )
                if should_pass:
                    passed = r.status_code == 200
                    self.test(f"longitude={lon}", "Boundary", passed, f"Status: {r.status_code}")
                else:
                    passed = r.status_code == 422
                    self.test(f"longitude={lon}", "Boundary", passed, f"Status: {r.status_code} (expected 422)")
            except Exception as e:
                self.test(f"longitude={lon}", "Boundary", False, str(e)[:50])

    def test_api_frame_count_bounds(self):
        """Test frame_count boundary validation"""
        self.print_section("3. API BOUNDARY TESTING: Frame Count Validation")
        
        test_cases = [
            (1, "min_invalid", False),
            (2, "min_valid", True),
            (10000, "max_valid", True),
            (10001, "max_invalid", False),
            (-1, "negative", False),
        ]
        
        for count, desc, should_pass in test_cases:
            try:
                r = self.session.post(
                    f"{self.api_base}/batch-earth-observations",
                    json={
                        "locations": [{"latitude": 0, "longitude": 0}],
                        "date": "2026-08-01",
                        "frame_count": count
                    },
                    timeout=5
                )
                if should_pass:
                    passed = r.status_code == 200
                    self.test(f"frame_count={count}", "Boundary", passed, f"Status: {r.status_code}")
                else:
                    passed = r.status_code == 422
                    self.test(f"frame_count={count}", "Boundary", passed, f"Status: {r.status_code} (expected 422)")
            except Exception as e:
                self.test(f"frame_count={count}", "Boundary", False, str(e)[:50])

    # ─── Error Handling & Information Disclosure ────────────────────────────────
    
    def test_error_disclosure(self):
        """Test that errors don't expose stack traces or internal details"""
        self.print_section("4. ERROR HANDLING: Information Disclosure Testing")
        
        test_cases = [
            ("GET", f"{self.api_base}/nonexistent", None, "404_not_found"),
            ("POST", f"{self.api_base}/sun-position", {"invalid": "data"}, "invalid_json"),
            ("POST", f"{self.api_base}/sun-position", {"latitude": "invalid"}, "invalid_type"),
        ]
        
        dangerous_keywords = ["traceback", "stacktrace", "file", "line", "function", "import", "module", ".py"]
        
        for method, url, data, desc in test_cases:
            try:
                if method == "GET":
                    r = self.session.get(url, timeout=5)
                else:
                    r = self.session.post(url, json=data, timeout=5)
                
                response_text = r.text.lower()
                contains_dangerous = any(kw in response_text for kw in dangerous_keywords)
                passed = not contains_dangerous
                self.test(f"error_{desc}", "Error Handling", passed, f"Status: {r.status_code}, Clean: {passed}")
            except Exception as e:
                self.test(f"error_{desc}", "Error Handling", False, str(e)[:50])

    # ─── CORS Testing ──────────────────────────────────────────────────────────
    
    def test_cors_headers(self):
        """Test CORS headers enforcement"""
        self.print_section("5. CORS VALIDATION: Cross-Origin Resource Sharing")
        
        test_origins = [
            ("https://malicious.com", False, "external_origin"),
            ("https://castlecelestialview.net", True, "same_origin"),
            (None, True, "no_origin"),
        ]
        
        for origin, should_allow, desc in test_origins:
            try:
                headers = {"Origin": origin} if origin else {}
                r = self.session.options(
                    f"{self.api_base}/sun-position",
                    headers=headers,
                    timeout=5
                )
                
                cors_header = r.headers.get("Access-Control-Allow-Origin", "").lower()
                
                if should_allow:
                    # Should allow same-origin or have CORS configured
                    passed = cors_header in ["*", origin] or "access-control" not in str(r.headers).lower()
                else:
                    # Should NOT allow cross-origin
                    passed = origin not in cors_header
                
                self.test(f"cors_{desc}", "CORS", passed, f"ACAO: {cors_header[:30]}")
            except Exception as e:
                self.test(f"cors_{desc}", "CORS", False, str(e)[:50])

    # ─── Security Headers Testing ──────────────────────────────────────────────
    
    def test_security_headers(self):
        """Test for presence of security headers"""
        self.print_section("6. SECURITY HEADERS: Verification")
        
        required_headers = {
            "Strict-Transport-Security": "HSTS",
            "Content-Security-Policy": "CSP",
            "X-Frame-Options": "Clickjacking",
            "X-Content-Type-Options": "MIME Sniffing",
            "Referrer-Policy": "Referrer",
        }
        
        try:
            r = self.session.get(f"{self.target}/", timeout=5)
            
            for header, desc in required_headers.items():
                present = header in r.headers
                self.test(f"header_{desc}", "Security Headers", present, f"Present: {present}")
                if present:
                    value = r.headers[header]
                    print(f"      -> Value: {value[:60]}...")
        except Exception as e:
            self.test("security_headers_fetch", "Security Headers", False, str(e)[:50])

    # ─── Request Size Limiting ────────────────────────────────────────────────
    
    def test_request_size_limits(self):
        """Test that large payloads are rejected"""
        self.print_section("7. DOS PROTECTION: Request Size Limits")
        
        try:
            # 6 MB payload (should exceed 5 MB limit)
            large_payload = {'x': 'y' * (6 * 1024 * 1024)}
            r = self.session.post(
                f"{self.api_base}/sun-position",
                json=large_payload,
                timeout=5
            )
            
            passed = r.status_code == 413  # Payload Too Large expected
            self.test("payload_6mb", "DOS Protection", passed, f"Status: {r.status_code} (expected 413)")
        except requests.exceptions.ConnectionError:
            # Connection reset is also valid response to large payload
            self.test("payload_6mb", "DOS Protection", True, "Connection rejected")
        except Exception as e:
            self.test("payload_6mb", "DOS Protection", False, str(e)[:50])

    # ─── TLS/SSL Testing ───────────────────────────────────────────────────────
    
    def test_tls_configuration(self):
        """Test TLS configuration and cipher suites"""
        self.print_section("8. TLS/SSL CONFIGURATION: Cipher Verification")
        
        try:
            import ssl
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # Get the target domain
            host = self.target.replace("https://", "").replace("http://", "")
            
            with ssl.create_connection((host, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    protocol = ssock.version
                    cipher = ssock.cipher()
                    cert = ssock.getpeercert()
                    
                    # TLSv1.2 or higher expected
                    tls_valid = "TLSv1.2" in protocol or "TLSv1.3" in protocol
                    self.test("tls_version", "TLS Config", tls_valid, f"Protocol: {protocol}")
                    
                    # Check cipher is secure (ECDHE recommended)
                    cipher_secure = "ECDHE" in cipher[0] or "DHE" in cipher[0]
                    self.test("cipher_suite", "TLS Config", cipher_secure, f"Cipher: {cipher[0][:40]}")
        except Exception as e:
            self.test("tls_config", "TLS Config", False, str(e)[:50])

    # ─── Input Fuzzing ─────────────────────────────────────────────────────────
    
    def test_input_fuzzing(self):
        """Test API resilience with malformed/unexpected input"""
        self.print_section("9. INPUT FUZZING: Malformed Data Testing")
        
        fuzz_cases = [
            ({"latitude": "abc", "longitude": 0, "date": "2026-08-01", "time": "12:00:00"}, "string_latitude"),
            ({"latitude": None, "longitude": 0, "date": "2026-08-01", "time": "12:00:00"}, "null_latitude"),
            ({"latitude": [], "longitude": 0, "date": "2026-08-01", "time": "12:00:00"}, "array_latitude"),
            ({"latitude": {}, "longitude": 0, "date": "2026-08-01", "time": "12:00:00"}, "object_latitude"),
            ({"latitude": 0, "longitude": 0, "date": "not-a-date", "time": "12:00:00"}, "invalid_date"),
        ]
        
        for payload, desc in fuzz_cases:
            try:
                r = self.session.post(
                    f"{self.api_base}/sun-position",
                    json=payload,
                    timeout=5
                )
                
                # Should reject with 422 (validation error)
                passed = r.status_code in [400, 422]  # Client error expected
                self.test(f"fuzz_{desc}", "Input Fuzzing", passed, f"Status: {r.status_code}")
            except Exception as e:
                self.test(f"fuzz_{desc}", "Input Fuzzing", False, str(e)[:50])

    # ─── Report Generation ─────────────────────────────────────────────────────
    
    def print_summary(self):
        """Print summary statistics"""
        passed = sum(1 for t in self.results['tests'] if t['passed'])
        total = len(self.results['tests'])
        passed_pct = (passed / total * 100) if total > 0 else 0
        
        self.print_section("PHASE 2 SUMMARY")
        print(f"Tests Passed: {passed}/{total} ({passed_pct:.1f}%)")
        print(f"Target: {self.target}")
        print(f"Timestamp: {self.results['timestamp']}")
        
        # Group by category
        categories = {}
        for test in self.results['tests']:
            cat = test['category']
            if cat not in categories:
                categories[cat] = {'passed': 0, 'failed': 0}
            if test['passed']:
                categories[cat]['passed'] += 1
            else:
                categories[cat]['failed'] += 1
        
        print("\nBy Category:")
        for cat in sorted(categories.keys()):
            stats = categories[cat]
            total_cat = stats['passed'] + stats['failed']
            pct = (stats['passed'] / total_cat * 100) if total_cat > 0 else 0
            print(f"  {cat:20} {stats['passed']}/{total_cat} passed ({pct:.0f}%)")

    def run_all_tests(self):
        """Run all security tests"""
        print(f"\n{'='*120}")
        print(f"  PHASE 2: DYNAMIC SECURITY TESTING")
        print(f"  Target: {self.target}")
        print(f"  {'='*120}\n")
        
        try:
            self.test_api_latitude_bounds()
            self.test_api_longitude_bounds()
            self.test_api_frame_count_bounds()
            self.test_error_disclosure()
            self.test_cors_headers()
            self.test_security_headers()
            self.test_request_size_limits()
            self.test_tls_configuration()
            self.test_input_fuzzing()
            self.print_summary()
            
            return self.results
        except KeyboardInterrupt:
            print("\n\n⚠️  Testing interrupted by user")
            self.print_summary()
            return self.results


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <target_url>")
        print(f"Example: {sys.argv[0]} https://castlecelestialview.net")
        print(f"Example: {sys.argv[0]} http://localhost:8000")
        sys.exit(1)
    
    target = sys.argv[1]
    tester = SecurityTester(target)
    results = tester.run_all_tests()
    
    # Save results to JSON
    output_file = f"phase2-results-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n[SAVED] Results saved to: {output_file}\n")


if __name__ == "__main__":
    main()
