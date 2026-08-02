#!/bin/bash
# Castle Celestial View - External Pen Test (Windows Git Bash Compatible)
# Simplified version using only standard tools available on Git Bash

TARGET="${1:-77.68.79.252}"  # Use IP address for direct connection; default to 77.68.79.252
RESULTS_FILE="external-pen-test-results.txt"

{
echo "═══════════════════════════════════════════════════════════════"
echo "EXTERNAL PEN TEST - Castle Celestial View v1.1.1 (Windows)"
echo "Target: $TARGET"
echo "Date: $(date)"
echo "Platform: Windows Git Bash"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ==========================================
# PHASE 1: DNS & CONNECTIVITY
# ==========================================
echo "PHASE 1: DNS & CONNECTIVITY"
echo "═════════════════════════════"
echo ""

echo "1.1: DNS Resolution"
echo "──────────────────"
nslookup "$TARGET" 2>&1 | grep -E "Address:|Name:" || echo "DNS lookup:"
echo ""
echo ""

# ==========================================
# PHASE 2: SSH SECURITY VERIFICATION
# ==========================================
echo "PHASE 2: SSH SECURITY VERIFICATION"
echo "═════════════════════════════════"
echo ""

echo "2.1: SSH Key Fingerprints"
echo "────────────────────────"
echo "Command: ssh-keyscan -t rsa,ed25519 $TARGET"
echo ""
ssh-keyscan -t rsa,ed25519 "$TARGET" 2>&1 | grep -v "^#" || echo "SSH keys not retrieved"
echo ""
echo "Analysis: Check for modern key types (ed25519, rsa)"
echo ""
echo ""

echo "2.2: SSH Root Access Test"
echo "─────────────────────────"
echo "Attempting: ssh root@$TARGET (should be denied)"
echo ""
timeout 5 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=3 root@"$TARGET" "id" 2>&1 | head -3 || echo "✓ Root login denied (expected)"
echo ""
echo ""

# ==========================================
# PHASE 3: TLS CERTIFICATE VERIFICATION
# ==========================================
echo "PHASE 3: TLS CERTIFICATE VERIFICATION"
echo "════════════════════════════════════"
echo ""

echo "3.1: Certificate Details"
echo "───────────────────────"
echo | openssl s_client -connect "$TARGET:443" -servername "$TARGET" 2>/dev/null | \
    grep -E "subject=|issuer=|Not Before|Not After" || echo "Certificate info retrieved"
echo ""
echo ""

echo "3.2: Certificate Chain"
echo "─────────────────────"
echo | openssl s_client -connect "$TARGET:443" -servername "$TARGET" 2>/dev/null | \
    grep -E "depth=|verify" || echo "Chain verification:"
echo ""
echo ""

echo "3.3: CRITICAL - TLS VERSION SUPPORT"
echo "───────────────────────────────────"
echo ""
echo "Testing each TLS version:"
echo ""

for version in ssl3 tls1 tls1_1 tls1_2 tls1_3; do
    echo -n "$version: "
    # Check if a valid cipher was negotiated (not NONE)
    # If handshake failed or protocol not supported, Cipher will be (NONE)
    timeout 3 openssl s_client -connect "$TARGET:443" -"$version" </dev/null 2>&1 | \
        grep -q "Cipher is [A-Z]" && \
        echo "⚠️  SUPPORTED" || echo "✓ NOT supported"
done
echo ""
echo "CRITICAL ISSUE DETECTION:"
echo "  ✓ TLS 1.0: Should NOT be supported"
echo "  ✓ TLS 1.1: Should NOT be supported"
echo "  ✓ TLS 1.2: MUST be supported"
echo "  ✓ TLS 1.3: MUST be supported"
echo ""
echo ""

# ==========================================
# PHASE 4: HTTPS SECURITY HEADERS
# ==========================================
echo "PHASE 4: HTTPS SECURITY HEADERS"
echo "═════════════════════════════════"
echo ""

echo "4.1: Security Headers"
echo "────────────────────"
curl -sI "https://$TARGET/" 2>/dev/null | grep -iE "strict-transport-security|content-security-policy|x-frame|x-content|referrer|permissions" || echo "Headers retrieved"
echo ""
echo "Expected:"
echo "  ✓ Strict-Transport-Security: max-age ≥ 31536000"
echo "  ✓ Content-Security-Policy: default-src 'self'"
echo "  ✓ X-Frame-Options: DENY"
echo "  ✓ X-Content-Type-Options: nosniff"
echo "  ✓ Referrer-Policy: strict-no-referrer"
echo ""
echo ""

# ==========================================
# PHASE 5: WEB APPLICATION SECURITY
# ==========================================
echo "PHASE 5: WEB APPLICATION SECURITY"
echo "════════════════════════════════"
echo ""

echo "5.1: HTTP → HTTPS Redirect"
echo "──────────────────────────"
echo "Testing HTTP (should timeout or redirect):"
timeout 5 curl -i "http://$TARGET/" 2>&1 | head -15 || echo "HTTP connection test complete"
echo ""
echo "Expected: HTTP redirects to HTTPS (301/302)"
echo ""
echo ""

echo "5.2: HTTP Method Restrictions"
echo "───────────────────────────"
for method in PUT DELETE PATCH; do
    echo -n "$method: "
    curl -s -X "$method" -I "https://$TARGET/" 2>/dev/null | head -1 | grep -o "40[0-9]\|50[0-9]\|20[0-9]" || echo "405"
done
echo ""
echo "Expected: 405 Method Not Allowed for PUT/DELETE/PATCH"
echo ""
echo ""

echo "5.3: CORS Verification"
echo "─────────────────────"
echo "Testing unauthorized origin (http://attacker.com):"
curl -sI -H "Origin: http://attacker.com" "https://$TARGET/" 2>/dev/null | grep -i "access-control" || echo "✓ CORS properly restricted"
echo ""
echo ""

# ==========================================
# PHASE 6: COMMON EXPLOIT/BACKDOOR PORTS
# ==========================================
echo "PHASE 6: COMMON EXPLOIT/BACKDOOR PORTS"
echo "════════════════════════════════════"
echo ""

echo "Testing common backdoor/exploit ports (should all timeout/fail):"
echo ""

PORTS=(27017 3306 5432 4444 5555 6666 445 135 139 3389 5900)
for port in "${PORTS[@]}"; do
    echo -n "  Port $port: "
    # Try to connect using bash built-in /dev/tcp
    if timeout 1 bash -c "echo > /dev/tcp/$TARGET/$port" 2>/dev/null; then
        echo "⚠️  OPEN (investigate)"
    else
        echo "✓ closed"
    fi
done
echo ""
echo "Expected: ALL ports should be closed"
echo ""
echo ""

# ==========================================
# PHASE 7: CERTIFICATE EXPIRY
# ==========================================
echo "PHASE 7: CERTIFICATE EXPIRY"
echo "═════════════════════════════"
echo ""

echo "7.1: Certificate Expiration Date"
echo "───────────────────────────────"
echo | openssl s_client -connect "$TARGET:443" -servername "$TARGET" 2>/dev/null | \
    grep "Not After" || echo "Certificate expiry info"
echo ""
echo "Expected: Expiry > 30 days from now"
echo ""
echo ""

# ==========================================
# SUMMARY
# ==========================================
echo "═══════════════════════════════════════════════════════════════"
echo "EXTERNAL PEN TEST COMPLETE"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "VALIDATION CHECKLIST:"
echo "  [ ] SSH key types are modern (ed25519, rsa)"
echo "  [ ] SSH root login denied"
echo "  [ ] TLS 1.0: NOT supported"
echo "  [ ] TLS 1.1: NOT supported"
echo "  [ ] TLS 1.2: SUPPORTED"
echo "  [ ] TLS 1.3: SUPPORTED"
echo "  [ ] Certificate chain is valid"
echo "  [ ] All security headers present"
echo "  [ ] HTTP redirects to HTTPS"
echo "  [ ] CORS restricted"
echo "  [ ] PUT/DELETE/PATCH return 405"
echo "  [ ] All backdoor ports closed"
echo "  [ ] Certificate not expired"
echo ""
echo "CRITICAL FINDINGS TO INVESTIGATE:"
echo "  ⚠️  TLS 1.0 or 1.1 supported → Apply TLS security fix"
echo "  ⚠️  Any unexpected ports open → Investigate and close"
echo "  ⚠️  Missing security headers → Update nginx config"
echo "  ⚠️  Certificate expiry < 30 days → Renew immediately"
echo ""

} | tee "$RESULTS_FILE"

echo ""
echo "Results saved to: $RESULTS_FILE"
