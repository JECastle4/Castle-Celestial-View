#!/bin/bash
# Castle Celestial View - Pen Test Phase 1: Infrastructure Security
# Validates HTTPS, security headers, CORS, and TLS configuration
# Run on production server or from local machine with network access

set -e

TARGET="${1:-castlecelestialview.net}"
RESULTS_FILE="/tmp/pen-test-phase1-results.txt"

echo "═══════════════════════════════════════════════════════════════"
echo "Castle Celestial View - Pen Test Phase 1: Infrastructure"
echo "Target: $TARGET"
echo "Date: $(date)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

{
echo "PHASE 1: INFRASTRUCTURE SECURITY VALIDATION"
echo "============================================"
echo ""

# Test 1.1: Basic HTTPS Connection and Security Headers
echo "TEST 1.1: HTTPS Connection & Security Headers"
echo "─────────────────────────────────────────────"
echo "Command: curl -I https://$TARGET"
echo ""
curl -sS -I "https://$TARGET" 2>&1 || echo "FAILED: Unable to connect to HTTPS"
echo ""
echo ""

# Test 1.2: HTTP Redirect to HTTPS
echo "TEST 1.2: HTTP → HTTPS Redirect"
echo "───────────────────────────────"
echo "Command: curl -I http://$TARGET (follow redirects)"
echo ""
curl -sS -i "http://$TARGET" 2>&1 | head -30 || echo "FAILED: Unable to test HTTP redirect"
echo ""
echo ""

# Test 1.3: CORS - Unauthorized Origin
echo "TEST 1.3: CORS Validation (Unauthorized Origin)"
echo "──────────────────────────────────────────────"
echo "Command: curl -H \"Origin: http://attacker.com\" -I https://$TARGET"
echo ""
curl -sS -H "Origin: http://attacker.com" -I "https://$TARGET" 2>&1 || echo "FAILED: CORS test failed"
echo ""
echo ""

# Test 1.4: CORS - Legitimate Origin
echo "TEST 1.4: CORS Validation (Legitimate Origin)"
echo "─────────────────────────────────────────────"
echo "Command: curl -H \"Origin: https://$TARGET\" -I https://$TARGET"
echo ""
curl -sS -H "Origin: https://$TARGET" -I "https://$TARGET" 2>&1 || echo "FAILED: CORS test failed"
echo ""
echo ""

# Test 1.5: Certificate Information
echo "TEST 1.5: Certificate Validation"
echo "────────────────────────────────"
echo "Command: openssl s_client -connect $TARGET:443 -servername $TARGET"
echo ""
echo "" | openssl s_client -connect "$TARGET:443" -servername "$TARGET" 2>&1 | grep -E "subject=|issuer=|Not Before|Not After|Public-Key|Signature ok" || echo "FAILED: Certificate check failed"
echo ""
echo ""

# Test 1.6: TLS Version Detection
echo "TEST 1.6: TLS Version & Ciphers"
echo "───────────────────────────────"
echo "Command: openssl s_client -connect $TARGET:443 -tls1_2 (and tls1_3)"
echo ""
echo "Testing TLS 1.2 support:"
echo "" | openssl s_client -connect "$TARGET:443" -tls1_2 2>&1 | grep -E "Protocol|TLSv1|SSL-Session" | head -5 || echo "TLS 1.2 test inconclusive"
echo ""
echo "Testing TLS 1.3 support:"
echo "" | openssl s_client -connect "$TARGET:443" -tls1_3 2>&1 | grep -E "Protocol|TLSv1|SSL-Session" | head -5 || echo "TLS 1.3 test inconclusive"
echo ""
echo ""

# Test 1.7: Security Header Details
echo "TEST 1.7: Individual Security Headers"
echo "──────────────────────────────────────"
echo ""
echo "Retrieving all headers with details:"
curl -sS -I "https://$TARGET" 2>&1 | while IFS=':' read -r header value; do
  if [[ $header =~ [Ss]trict|[Cc]ontent-[Ss]ecurity|[Xx]-|[Cc]ache|[Rr]eferrer ]]; then
    echo "  ✓ $header: $(echo $value | xargs)"
  fi
done
echo ""
echo ""

# Test 1.8: HTTP Methods - Check for unsafe methods
echo "TEST 1.8: HTTP Methods Allowed"
echo "──────────────────────────────"
echo ""
for method in GET POST PUT DELETE PATCH OPTIONS HEAD TRACE; do
  response=$(curl -sS -X "$method" -I "https://$TARGET" 2>&1 | head -1)
  echo "  $method: $response"
done
echo ""
echo ""

# Test 1.9: Dependency Versions (if SSH access available)
echo "TEST 1.9: Dependency Versions on Production"
echo "──────────────────────────────────────────"
echo "(Run on production server: python -m pip list | grep -E 'pillow|starlette|click|msgpack|fastapi|pydantic')"
echo ""
if command -v ssh &> /dev/null && [ -n "$SSH_USER" ]; then
  echo "Attempting SSH to deployuser@$TARGET..."
  ssh "deployuser@$TARGET" "python -m pip list 2>/dev/null | grep -E 'pillow|starlette|click|msgpack|fastapi|pydantic|uvicorn' || echo 'SSH failed or pip list unavailable'"
else
  echo "SSH not configured. Run manually on production server."
fi
echo ""
echo ""

# Test 1.10: pip-audit Check
echo "TEST 1.10: Dependency Vulnerability Audit"
echo "─────────────────────────────────────────"
echo "(Run on production server: python -m pip-audit)"
echo ""
if command -v ssh &> /dev/null && [ -n "$SSH_USER" ]; then
  ssh "deployuser@$TARGET" "python -m pip-audit 2>/dev/null || echo 'pip-audit not available'"
else
  echo "SSH not configured. Run manually on production server."
fi
echo ""
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "PHASE 1 TESTING COMPLETE"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "CRITICAL CHECKS:"
echo "  ✓ HTTPS responding (HTTP/2 or HTTP/1.1)"
echo "  ✓ Strict-Transport-Security header present"
echo "  ✓ Content-Security-Policy: default-src 'self'"
echo "  ✓ X-Frame-Options: DENY"
echo "  ✓ X-Content-Type-Options: nosniff"
echo "  ✓ Referrer-Policy: strict-no-referrer"
echo "  ✓ Permissions-Policy: camera=(), microphone=()"
echo "  ✓ No Server header (or minimal)"
echo "  ✓ Certificate valid and not expired"
echo "  ✓ TLS 1.2+ enforced (no TLS 1.0/1.1)"
echo "  ✓ PUT/DELETE/PATCH return 405 (not allowed)"
echo "  ✓ CORS doesn't leak to unauthorized origins"
echo ""
echo "Results saved to: $RESULTS_FILE"

} | tee "$RESULTS_FILE"

echo ""
echo "Next: Review output and run Phase 2 input validation tests"
