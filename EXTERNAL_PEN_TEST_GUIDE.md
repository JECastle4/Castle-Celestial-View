# External Pen Testing Checklist
## Verify Production Security from Outside Network

**Important:** These tests should be run from a machine **outside** your production network to simulate an attacker's perspective.

---

## Prerequisites

### Required Tools (Install on your local machine)

```bash
# macOS (via Homebrew)
brew install nmap curl openssl

# Ubuntu/Debian
sudo apt-get install nmap curl openssl netcat-openbsd dnsutils traceroute

# Windows (via Chocolatey or download directly)
choco install nmap curl openssl
```

### Optional but Recommended
```bash
# Nikto (web server scanner)
sudo apt-get install nikto

# OWASP ZAP (GUI-based, download from: https://www.zaproxy.org/)

# sslscan (TLS vulnerability scanner)
sudo apt-get install sslscan
```

---

## Quick Verification Commands (Run from local machine)

### 1. PORT SCANNING - Verify Only 22 & 443 Open

```bash
# Full port scan (slow, ~5 minutes)
nmap -p- 77.68.79.252

# Expected output:
# 22/tcp   open  ssh
# 443/tcp  open  https
# All other ports: filtered or closed
```

**Critical Finding If:**
- Any other ports are open (except 22, 443)
- Services running on unexpected ports
- Backdoor ports responding (27017, 3306, 5432, etc.)

---

### 2. SSH SECURITY CHECK

```bash
# Verify OpenSSH version
ssh-keyscan -t rsa,ed25519 castlecelestialview.net

# Try root login (should fail)
ssh root@castlecelestialview.net
# Expected: Permission denied

# Check SSH config (if you have access)
ssh deployuser@castlecelestialview.net "sudo sshd -T | grep -E 'permitrootlogin|passwordauth|pubkeyauth'"
# Expected:
#   permitrootlogin: no
#   passwordauthentication: no
#   pubkeyauthentication: yes
```

---

### 3. TLS/CERTIFICATE VERIFICATION

```bash
# Check certificate details
openssl s_client -connect castlecelestialview.net:443 -servername castlecelestialview.net

# Should show:
#   - subject: CN=castlecelestialview.net
#   - issuer: C=US, O=Let's Encrypt
#   - Not Before/After dates (check expiry > 30 days)
#   - Verify return code: 0 (ok)

# Verify certificate chain is complete
curl -vI https://castlecelestialview.net 2>&1 | grep -A5 "certificate"

# Test TLS 1.2
openssl s_client -connect castlecelestialview.net:443 -tls1_2

# Test TLS 1.3
openssl s_client -connect castlecelestialview.net:443 -tls1_3

# SHOULD NOT connect with:
# openssl s_client -connect castlecelestialview.net:443 -ssl3
# openssl s_client -connect castlecelestialview.net:443 -tls1
# openssl s_client -connect castlecelestialview.net:443 -tls1_1
```

---

### 4. SECURITY HEADERS CHECK

```bash
# Retrieve all headers
curl -I https://castlecelestialview.net

# Expected:
# HTTP/2 200
# strict-transport-security: max-age=31536000; includeSubDomains; preload
# content-security-policy: default-src 'self'; ...
# x-frame-options: DENY
# x-content-type-options: nosniff
# referrer-policy: strict-no-referrer
# permissions-policy: camera=(); microphone=(); ...

# Check specific headers
curl -I https://castlecelestialview.net | grep -i "strict-transport-security\|content-security-policy\|x-frame-options"
```

---

### 5. HTTP METHOD RESTRICTION

```bash
# Test PUT (should return 405)
curl -X PUT -I https://castlecelestialview.net

# Test DELETE (should return 405)
curl -X DELETE -I https://castlecelestialview.net

# Test PATCH (should return 405)
curl -X PATCH -I https://castlecelestialview.net

# Test TRACE (should return 405 or not allowed)
curl -X TRACE -I https://castlecelestialview.net

# Expected: 405 Method Not Allowed for all unsafe methods
```

---

### 6. HTTP → HTTPS REDIRECT

```bash
# Test HTTP redirect
curl -i http://castlecelestialview.net

# Expected:
# HTTP/1.1 301 Moved Permanently
# Location: https://castlecelestialview.net/
```

---

### 7. CORS VERIFICATION

```bash
# Test unauthorized origin
curl -H "Origin: http://attacker.com" -I https://castlecelestialview.net

# Expected: No Access-Control-Allow-Origin header OR restricted origin only

# Test legitimate origin
curl -H "Origin: https://castlecelestialview.net" -I https://castlecelestialview.net

# Expected: Access-Control-Allow-Origin: https://castlecelestialview.net
```

---

### 8. NETWORK FOOTPRINT (Optional)

```bash
# Traceroute to target
traceroute castlecelestialview.net

# ICMP ping (may be blocked - that's ok)
ping -c 1 castlecelestialview.net

# DNS lookup
nslookup castlecelestialview.net
```

---

### 9. AUTOMATED SCANNING (If Available)

```bash
# Nikto web server scan
nikto -h castlecelestialview.net

# sslscan TLS vulnerability check
sslscan castlecelestialview.net

# Curl security headers audit
curl -I https://castlecelestialview.net | grep -iE "^(strict|content-security|x-frame|x-content|referrer|permissions)"
```

---

## Full Automated Script

Run the complete external pen test:

```bash
# From local machine (outside network)
bash ./scripts/external-pen-test.sh castlecelestialview.net
```

This will:
- ✅ Port scan (verify only 22, 443 open)
- ✅ SSH security check
- ✅ TLS certificate verification
- ✅ Security headers validation
- ✅ HTTP method restrictions
- ✅ CORS testing
- ✅ Backdoor detection
- ✅ Performance check
- ✅ Certificate expiry validation

---

## Critical Findings Reference

| Finding | Severity | Action |
|---------|----------|--------|
| Open port besides 22/443 | **CRITICAL** | Close immediately; investigate purpose |
| SSH root login allowed | **CRITICAL** | Disable in `/etc/ssh/sshd_config` |
| SSH password auth enabled | **CRITICAL** | Disable in `/etc/ssh/sshd_config` |
| TLS 1.0/1.1 enabled | **HIGH** | Disable in nginx config |
| Missing security headers | **HIGH** | Add to nginx config |
| Self-signed cert / expired | **HIGH** | Renew certificate immediately |
| HTTP doesn't redirect HTTPS | **HIGH** | Configure nginx redirect |
| CORS allows unauthorized origins | **HIGH** | Restrict in API middleware |
| Unsafe HTTP methods allowed | **MEDIUM** | Configure nginx/API restrictions |
| Error messages leak info | **MEDIUM** | Sanitize error responses |

---

## Backdoor Detection

Common ports to verify are closed:

| Port | Service | Should Be |
|------|---------|-----------|
| 445 | SMB | Closed |
| 135 | RPC | Closed |
| 139 | NetBIOS | Closed |
| 3306 | MySQL | Closed |
| 5432 | PostgreSQL | Closed |
| 27017 | MongoDB | Closed |
| 6379 | Redis | Closed |
| 4444 | Generic backdoor | Closed |
| 5555 | Generic backdoor | Closed |
| 3389 | RDP | Closed |
| 5900 | VNC | Closed |

---

## Verification Checklist

- [ ] Run `external-pen-test.sh` from outside network
- [ ] Verify only ports 22 and 443 respond
- [ ] Confirm SSH: root login denied
- [ ] Confirm SSH: password auth disabled
- [ ] Verify TLS 1.2+ enabled
- [ ] Verify TLS 1.0/1.1 disabled
- [ ] Verify certificate valid (not expired)
- [ ] Verify all security headers present
- [ ] Verify HTTP → HTTPS redirect working
- [ ] Verify CORS restricted to legitimate origins
- [ ] Verify PUT/DELETE/PATCH return 405
- [ ] Verify no common backdoor ports open
- [ ] Run nmap: only 22/443 open
- [ ] Check certificate expiry (>30 days remaining)
- [ ] Verify no information disclosure in error messages

---

## Example Running External Pen Test

```bash
# From your local machine (NOT on production server)
cd ~/Documents/Castle-Celestial-View
bash scripts/external-pen-test.sh castlecelestialview.net

# View results
cat /tmp/external-pen-test-results.txt

# Archive results
cp /tmp/external-pen-test-results.txt external-pen-test-2026-08-02.txt
```

---

## Documentation

Once completed, this provides evidence for:
- ✅ Production hardening verification
- ✅ Security audit trail
- ✅ Compliance documentation
- ✅ Issue #206 closure proof

