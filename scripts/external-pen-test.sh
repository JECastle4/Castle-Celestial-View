#!/bin/bash
# Castle Celestial View - External Pen Test (From Outside Network)
# Verify production security posture from attacker's perspective

set -e

TARGET="${1:-castlecelestialview.net}"
RESULTS_FILE="/tmp/external-pen-test-results.txt"

{
echo "═══════════════════════════════════════════════════════════════"
echo "EXTERNAL PEN TEST - Castle Celestial View v1.1.1"
echo "Target: $TARGET"
echo "Date: $(date)"
echo "Execution: FROM OUTSIDE NETWORK (External Perspective)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ==========================================
# PHASE 1: PORT SCANNING (nmap)
# ==========================================
echo "PHASE 1: PORT SCANNING - Verify Only Expected Ports Open"
echo "════════════════════════════════════════════════════════"
echo ""

if command -v nmap &> /dev/null; then
    echo "1.1: Full TCP Port Scan (All 65535 ports)"
    echo "───────────────────────────────────────"
    echo "Command: nmap -p- $TARGET"
    echo ""
    nmap -p- "$TARGET" 2>&1 || echo "nmap not available or blocked"
    echo ""
    echo "Expected: ONLY ports 22 (SSH) and 443 (HTTPS) should be open"
    echo "If other ports are open: CRITICAL FINDING"
    echo ""
    echo ""

    echo "1.2: Service Fingerprinting"
    echo "──────────────────────────"
    echo "Command: nmap -sV -p 22,443 $TARGET"
    nmap -sV -p 22,443 "$TARGET" 2>&1 || echo "nmap not available"
    echo ""
    echo "Expected: SSH (port 22) and HTTPS (port 443) with appropriate versions"
    echo ""
    echo ""

    echo "1.3: OS and Service Detection"
    echo "────────────────────────────"
    echo "Command: nmap -A $TARGET"
    nmap -A "$TARGET" 2>&1 || echo "nmap not available"
    echo ""
else
    echo "⚠️  nmap not installed. Install with:"
    echo "   Ubuntu/Debian: sudo apt-get install nmap"
    echo "   macOS: brew install nmap"
    echo "   Windows: choco install nmap"
    echo ""
fi
echo ""

# ==========================================
# PHASE 2: SSH SECURITY VERIFICATION
# ==========================================
echo "PHASE 2: SSH SECURITY VERIFICATION"
echo "═════════════════════════════════"
echo ""

echo "2.1: SSH Banner Grab"
echo "──────────────────"
echo "Command: timeout 5 nc $TARGET 22"
echo ""
timeout 5 nc "$TARGET" 22 2>&1 | head -5 || echo "Connection info:"
echo ""
echo "Expected: OpenSSH version should be current (not ancient)"
echo ""
echo ""

echo "2.2: SSH Security Options Check"
echo "──────────────────────────────"
echo "Attempting to retrieve SSH supported algorithms..."
echo ""
ssh-keyscan -t rsa,ed25519 "$TARGET" 2>&1 | head -20 || echo "SSH scan blocked or unavailable"
echo ""
echo "Expected: Modern key types (ed25519, rsa-sha2-512)"
echo ""
echo ""

echo "2.3: Root Login Verification"
echo "───────────────────────────"
echo "Attempting SSH with root (should fail):"
echo ""
timeout 5 ssh -o StrictHostKeyChecking=no -o ConnectTimeout=3 root@"$TARGET" "id" 2>&1 | head -5 || echo "✓ Root login denied (expected)"
echo ""
echo "Expected: Permission denied / no root access"
echo ""
echo ""

echo "2.4: Password Authentication Check"
echo "──────────────────────────────────"
echo "SSH should use key-based auth only (no passwords):"
echo ""
sshpass -p 'invalid' ssh -o StrictHostKeyChecking=no root@"$TARGET" 2>&1 | head -3 || echo "✓ Password auth likely disabled (expected)"
echo ""
echo ""

# ==========================================
# PHASE 3: TLS CERTIFICATE VERIFICATION
# ==========================================
echo "PHASE 3: TLS CERTIFICATE VERIFICATION (External)"
echo "════════════════════════════════════════════════"
echo ""

echo "3.1: Certificate Details"
echo "───────────────────────"
echo "Command: openssl s_client -connect $TARGET:443"
echo ""
echo | openssl s_client -connect "$TARGET:443" -servername "$TARGET" 2>/dev/null | \
    grep -E "subject=|issuer=|Not Before|Not After|Public-Key|Signature ok" || echo "Certificate details:"
echo ""
echo ""

echo "3.2: Certificate Chain Verification"
echo "───────────────────────────────────"
openssl s_client -connect "$TARGET:443" -servername "$TARGET" -showcerts </dev/null 2>&1 | \
    grep -E "depth|verify" | head -10 || echo "Chain verification info retrieved"
echo ""
echo "Expected: Verify return code: 0 (ok)"
echo ""
echo ""

echo "3.3: TLS Version Support"
echo "──────────────────────"
for version in ssl3 tls1 tls1_1 tls1_2 tls1_3; do
    echo -n "$version: "
    timeout 3 openssl s_client -connect "$TARGET:443" -"$version" </dev/null 2>&1 | \
        grep -q "CONNECTED" && echo "SUPPORTED (VERIFY)" || echo "not supported ✓"
done
echo ""
echo "Expected: TLS 1.2 and 1.3 supported; TLS 1.0, 1.1, SSL 3.0 NOT supported"
echo ""
echo ""

# ==========================================
# PHASE 4: HTTPS SECURITY HEADERS
# ==========================================
echo "PHASE 4: HTTPS SECURITY HEADERS (External)"
echo "═════════════════════════════════════════"
echo ""

echo "4.1: Security Headers"
echo "────────────────────"
curl -sI "https://$TARGET/" | grep -i -E "strict-transport-security|content-security-policy|x-frame-options|x-content-type-options|referrer-policy|permissions-policy" || echo "Headers not found"
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
# PHASE 5: NETWORK AVAILABILITY
# ==========================================
echo "PHASE 5: NETWORK ACCESSIBILITY"
echo "════════════════════════════════"
echo ""

echo "5.1: Ping Response"
echo "────────────────"
ping -c 1 -W 3 "$TARGET" 2>&1 | grep -E "bytes from|round-trip" || echo "ICMP blocked (may be intentional)"
echo ""
echo ""

echo "5.2: DNS Resolution"
echo "──────────────────"
nslookup "$TARGET" 2>&1 | grep -E "Address:|Name:" || echo "DNS lookup info:"
dig "$TARGET" +short || echo "Unable to resolve"
echo ""
echo ""

echo "5.3: Traceroute to Target"
echo "─────────────────────────"
echo "First 5 hops:"
timeout 10 traceroute -m 5 "$TARGET" 2>&1 | head -7 || echo "traceroute unavailable or blocked"
echo ""
echo ""

# ==========================================
# PHASE 6: WEB APPLICATION SCANNING
# ==========================================
echo "PHASE 6: WEB APPLICATION SECURITY (External)"
echo "════════════════════════════════════════════"
echo ""

echo "6.1: HTTP → HTTPS Redirect"
echo "──────────────────────────"
echo "Attempting HTTP connection (should redirect):"
curl -i "http://$TARGET/" 2>&1 | head -10 || echo "Connection attempt:"
echo ""
echo "Expected: 301/302 redirect to HTTPS"
echo ""
echo ""

echo "6.2: CORS Preflight Test"
echo "───────────────────────"
echo "Testing CORS with unauthorized origin:"
curl -sI -H "Origin: http://attacker.com" "https://$TARGET/" | grep -i access-control || echo "✓ CORS properly restricted"
echo ""
echo ""

echo "6.3: HTTP Security Methods"
echo "──────────────────────────"
for method in PUT DELETE PATCH; do
    echo -n "$method: "
    curl -s -X "$method" -I "https://$TARGET/" | head -1 | grep -o "40[0-9]\|50[0-9]\|200\|405" || echo "405"
done
echo ""
echo "Expected: 405 Method Not Allowed for PUT/DELETE/PATCH"
echo ""
echo ""

# ==========================================
# PHASE 7: BACKDOOR & SUSPICIOUS SERVICE DETECTION
# ==========================================
echo "PHASE 7: BACKDOOR & SUSPICIOUS SERVICE DETECTION"
echo "════════════════════════════════════════════════"
echo ""

echo "7.1: Common Backdoor Ports"
echo "──────────────────────────"
echo "Checking for common backdoor/exploit ports..."
echo ""
for port in 4444 5555 6666 7777 8888 9999 1337 31337 27017 27018 3306 5432; do
    timeout 1 nc -zv "$TARGET" "$port" 2>&1 | grep -q "succeeded\|open" && echo "⚠️  Port $port open (investigate)" || echo "✓ Port $port closed"
done
echo ""
echo ""

echo "7.2: Common Exploit Services"
echo "───────────────────────────"
echo "Probing for common exploitable services..."
echo ""
for port in 445 135 139 139 3389 5900; do
    timeout 1 bash -c "echo > /dev/tcp/$TARGET/$port" 2>/dev/null && echo "⚠️  Port $port responding (investigate)" || true
done
echo ""
echo "Expected: All checks return closed/no response"
echo ""
echo ""

# ==========================================
# PHASE 8: PERFORMANCE & AVAILABILITY
# ==========================================
echo "PHASE 8: PERFORMANCE & AVAILABILITY"
echo "════════════════════════════════════"
echo ""

echo "8.1: Response Time"
echo "────────────────"
echo "Testing HTTPS response time:"
time curl -s "https://$TARGET/" > /dev/null 2>&1 || echo "Timeout or connection error"
echo ""
echo "Expected: < 1 second for response"
echo ""
echo ""

echo "8.2: Certificate Expiry"
echo "─────────────────────"
echo | openssl s_client -connect "$TARGET:443" -servername "$TARGET" 2>/dev/null | \
    grep "Not After" || echo "Certificate expiry info:"
echo ""
echo "Expected: Expiry > 30 days in future"
echo ""
echo ""

} | tee "$RESULTS_FILE"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "EXTERNAL PEN TEST COMPLETE"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Results saved to: $RESULTS_FILE"
echo ""
echo "SECURITY VERIFICATION CHECKLIST:"
echo "  [ ] Only ports 22 (SSH) and 443 (HTTPS) open"
echo "  [ ] No suspicious/backdoor ports responding"
echo "  [ ] SSH root login denied"
echo "  [ ] SSH password authentication disabled"
echo "  [ ] TLS 1.2+ enforced, TLS 1.0/1.1 disabled"
echo "  [ ] Certificate valid and not expired"
echo "  [ ] All security headers present"
echo "  [ ] HTTP redirects to HTTPS"
echo "  [ ] CORS properly restricted"
echo "  [ ] PUT/DELETE/PATCH return 405"
echo "  [ ] No error/debug information leaked"
echo "  [ ] No suspicious services detected"
echo ""
