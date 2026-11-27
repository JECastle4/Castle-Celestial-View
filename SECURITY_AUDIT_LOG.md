# Security Audit Log - Castle Celestial View

## Audit Entry: 2026-11-27 - External Pen Test (v1.2.0)

**Date:** November 27, 2026  
**Time:** 18:00-18:40 UTC  
**Tester:** Manual run of EXTERNAL_PEN_TEST_GUIDE.md steps from a Windows laptop (nmap 7.80, OpenSSL, curl.exe)  
**Target:** castlecelestialview.net (77.68.79.252)  
**Release:** v1.2.0  
**Status:** ⚠️ PASSED WITH FOLLOW-UPS (1 finding to review)  
**Full results:** `scripts/external-pen-test-results-v1.2.0.txt`

### Results by Step

| Step | Check | Result | Details |
|------|-------|--------|---------|
| 1 | Port scan (`nmap -p-`) | ✅ PASS | Only 22/tcp and 443/tcp open; 65533 filtered |
| 2 | SSH security | ⚠️ REVIEW | Root login denied; server offers `publickey,password` (password auth appears enabled); host key scan and `sshd -T` inconclusive |
| 3 | TLS / certificate | ✅ PASS | Let's Encrypt, chain verified, expires 2027-02-24 (~89 days); TLS 1.2 and 1.3 only (1.0/1.1 not offered, confirmed by nmap); all ciphers grade A |
| 4 | Security headers | ✅ PASS | HSTS, CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy present; `Server: nginx` (no version) |
| 5 | HTTP methods | ✅ PASS | PUT, DELETE, PATCH, TRACE all return 405 |
| 6 | HTTP to HTTPS redirect | ➖ N/A | Port 80 filtered (connection times out); no redirect and no cleartext exposure |
| 7 | CORS | ✅ PASS | Untrusted origin gets no ACAO header; preflight rejected 400 "Disallowed CORS origin" |
| 8 | Network footprint | ✅ PASS | ICMP filtered; DNS resolves to 77.68.79.252 |
| 9 | Automated scanning | ✅ PASS | nikto/sslscan/ZAP not available (not run); nmap HTTP scripts run; raw-IP access gets no response, so the nmap "HSTS not configured" result is a scanner artifact |

### Findings & Follow-ups

1. **SSH password authentication appears enabled (Medium, needs confirmation).** The root login attempt reported `Permission denied (publickey,password)` and `deployuser` was prompted for a password. The guide expects `passwordauthentication no`. Verify the effective config with `sudo sshd -T | grep -E 'permitrootlogin|passwordauth|pubkeyauth'` (check `/etc/ssh/sshd_config.d/*.conf` for overrides) and disable if key-only is intended.
2. **Host keys not retrieved (Info).** Windows `ssh-keyscan` does not support the server's `sntrup761x25519` KEX; re-run from Git Bash/WSL if key fingerprints are needed.
3. **No HTTP to HTTPS redirect (Low/Info).** Port 80 is filtered by design; optionally open it only to serve a 301.
4. **CSP `style-src 'unsafe-inline'` (Low advisory).** `script-src` is strict `'self'`.
5. **Legacy TLS 1.2 suites (Low advisory).** CBC-SHA, CAMELLIA, ARIA and AES-CCM_8 suites remain enabled; none are known-vulnerable.
6. **IPv6 record (Info).** The Aug 2026 audit recorded an AAAA record; this lookup returned IPv4 only. Confirm whether that is intentional.

### Conclusion

No critical findings. Perimeter, TLS, headers, method restriction and CORS controls are intact on v1.2.0. The SSH password-authentication item should be confirmed and, if unintended, remediated before the next audit.

---

## Audit Entry: 2026-08-02 - TLS 1.0/1.1 Vulnerability Remediation

**Date:** August 2, 2026  
**Time:** 17:28 UTC  
**Tester:** External Pen Test Script (corrected v1.1.1-patch1)  
**Target:** castlecelestialview.net (77.68.79.252)  
**Release:** v1.1.1-patch1  
**Status:** ✅ PASSED

### Vulnerability Identified & Fixed

| Item | Status | Details |
|------|--------|---------|
| **CVE-2016-2107** | ✅ FIXED | TLS protocol downgrade attack |
| **TLS 1.0** | ✅ BLOCKED | "no protocols available" error |
| **TLS 1.1** | ✅ BLOCKED | "no protocols available" error |
| **TLS 1.2** | ✅ WORKING | ECDHE-ECDSA-AES256-GCM-SHA384 |
| **TLS 1.3** | ✅ WORKING | TLS_AES_256_GCM_SHA384 |

### Security Assessment Results

#### Phase 1: DNS & Connectivity ✅
- IPv4: 77.68.79.252
- IPv6: 2a0a:ef40:18df:5901:df91:e191:24ce:d99
- DNS Resolution: PASSED

#### Phase 2: SSH Security ✅
- Key Types: ed25519 (modern), RSA (modern)
- Root Login: DENIED
- Analysis: PASSED

#### Phase 3: TLS Certificate ✅
- Subject: CN=castlecelestialview.net
- Issuer: Let's Encrypt E7
- Certificate Chain: Valid
- Analysis: PASSED

#### Phase 4: HTTPS Security Headers ✅
- Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
- Content-Security-Policy: default-src 'self'
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-no-referrer
- Permissions-Policy: All dangerous features disabled
- Analysis: PASSED (All 6 headers present)

#### Phase 5: Web Application Security ✅
- HTTP → HTTPS Redirect: Working
- PUT/DELETE/PATCH Methods: 405 (correctly denied)
- CORS: Properly restricted
- Analysis: PASSED

#### Phase 6: Backdoor Ports ✅
- MongoDB (27017): CLOSED
- MySQL (3306): CLOSED
- PostgreSQL (5432): CLOSED
- Netcat (4444, 5555, 6666): CLOSED
- SMB (445, 135, 139): CLOSED
- RDP (3389): CLOSED
- VNC (5900): CLOSED
- Analysis: PASSED (All critical ports closed)

#### Phase 7: Certificate Expiry ✅
- Status: Valid and not expired
- Analysis: PASSED

### Remediation Details

**Files Modified:**
- `scripts/nginx.conf` - Line 33: Changed from `ssl_protocols TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;` to `ssl_protocols TLSv1.2 TLSv1.3;`
- `scripts/external-pen-test-windows.sh` - Fixed cipher detection logic (checks for valid cipher vs TCP CONNECTED)
- `scripts/castle-celestial.nginx.conf` - Already correct with TLS 1.2+ enforcement

**Commits:**
1. `39375d6` - Security: TLS 1.0/1.1 disabled in global nginx.conf, enforce TLS 1.2+ only (Issue #206)
2. `a73c713` - Fix: external-pen-test-windows.sh TLS detection logic - check for valid cipher instead of CONNECTED

**Tag:** v1.1.1-patch1

**Production Deployment:**
- Backup: `/etc/nginx/nginx.conf.backup.20260802-162332`
- Deployment Method: Downloaded from GitHub, validated, deployed
- Reloaded: nginx reloaded successfully (no downtime)

### Test Script Correction

**Original Bug:** Script checked for "CONNECTED" which TCP reports even on failed TLS handshakes  
**Fixed Logic:** Now checks for valid cipher negotiation (`Cipher is [ECDHE-...]` vs `Cipher is (NONE)`)  
**Impact:** Eliminates false positives when testing protocol support

### Conclusion

✅ **All security tests PASSED**  
✅ **TLS 1.0/1.1 vulnerability FIXED and VERIFIED**  
✅ **Production deployment SUCCESSFUL**  
✅ **Ready for release v1.1.1-patch1**

---

## Previous Audit Entries

### Initial Assessment: 2026-08-02 - Pre-Deployment (13:00 UTC)
**Finding:** External pen test revealed TLS 1.0 and 1.1 still accessible  
**Severity:** HIGH  
**Status:** VULNERABILITY CONFIRMED - Root cause identified as http-level nginx.conf override
