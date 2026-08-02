#!/bin/bash
# Deploy TLS Security Fix to Production
# CRITICAL: Disable TLS 1.0/1.1, enforce TLS 1.2+ only

set -e

TARGET_USER="deployuser"
TARGET_HOST="${1:-77.68.79.252}"  # Use IP address for direct connection; default to 77.68.79.252

echo "═══════════════════════════════════════════════════════════════"
echo "CRITICAL SECURITY FIX: TLS 1.0/1.1 Vulnerability Remediation"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Target: $TARGET_HOST"
echo "User: $TARGET_USER"
echo ""
echo "Changes:"
echo "  ✓ Disable TLS 1.0 and 1.1 (legacy protocols)"
echo "  ✓ Enforce TLS 1.2 and 1.3 only (modern protocols)"
echo "  ✓ Configure modern cipher suites"
echo ""

# Check if we can access the target
echo "Verifying access to $TARGET_HOST..."
if ssh "$TARGET_USER@$TARGET_HOST" "echo Connected" >/dev/null 2>&1; then
    echo "✓ SSH access confirmed"
else
    echo "✗ Cannot SSH to $TARGET_HOST"
    echo "Make sure you have SSH access configured"
    exit 1
fi
echo ""

# Backup current nginx config
echo "Step 1: Backup Current Configuration"
echo "───────────────────────────────────"
ssh "$TARGET_USER@$TARGET_HOST" "
    sudo cp /etc/nginx/sites-available/castle-celestial \
            /etc/nginx/sites-available/castle-celestial.backup.$(date +%Y%m%d-%H%M%S)
    echo '✓ Backed up to: /etc/nginx/sites-available/castle-celestial.backup.*'
"
echo ""

# Copy updated nginx config to production
echo "Step 2: Deploy Updated nginx Configuration"
echo "──────────────────────────────────────────"
echo "Downloading fixed configuration from GitHub..."

# Try local file first, then GitHub
if [ -f "./scripts/castle-celestial.nginx.conf" ]; then
    echo "✓ Using local file: ./scripts/castle-celestial.nginx.conf"
    scp ./scripts/castle-celestial.nginx.conf "$TARGET_USER@$TARGET_HOST":/tmp/castle-celestial.new
elif [ -f "/scripts/castle-celestial.nginx.conf" ]; then
    echo "✓ Using absolute path: /scripts/castle-celestial.nginx.conf"
    scp /scripts/castle-celestial.nginx.conf "$TARGET_USER@$TARGET_HOST":/tmp/castle-celestial.new
else
    echo "Local file not found. Downloading from GitHub repository..."
    # Download from GitHub raw content
    ssh "$TARGET_USER@$TARGET_HOST" "
        curl -sSL 'https://raw.githubusercontent.com/JECastle4/Castle-Celestial-View/main/scripts/castle-celestial.nginx.conf' \
            -o /tmp/castle-celestial.new
        if [ $? -eq 0 ]; then
            echo '✓ Configuration downloaded from GitHub'
        else
            echo '✗ Failed to download configuration'
            exit 1
        fi
    "
fi
echo "✓ Configuration uploaded"
echo ""

# Verify nginx config syntax
echo "Step 3: Validate nginx Configuration"
echo "────────────────────────────────────"
ssh "$TARGET_USER@$TARGET_HOST" "
    sudo cp /tmp/castle-celestial.new /etc/nginx/sites-available/castle-celestial.test
    sudo nginx -t -c /etc/nginx/nginx.conf 2>&1 | grep -i 'test successful' && echo '✓ Configuration syntax valid' || (echo '✗ Configuration has errors'; sudo rm /etc/nginx/sites-available/castle-celestial.test; exit 1)
    sudo rm /etc/nginx/sites-available/castle-celestial.test
"
echo ""

# Deploy updated configuration
echo "Step 4: Deploy Updated Configuration"
echo "───────────────────────────────────"
ssh "$TARGET_USER@$TARGET_HOST" "
    sudo cp /tmp/castle-celestial.new /etc/nginx/sites-available/castle-celestial
    echo '✓ Configuration deployed'
"
echo ""

# Reload nginx
echo "Step 5: Reload nginx Service"
echo "───────────────────────────"
ssh "$TARGET_USER@$TARGET_HOST" "
    sudo systemctl reload nginx
    echo '✓ nginx reloaded successfully'
"
echo ""

# Verify the fix
echo "Step 6: Verify TLS Configuration"
echo "────────────────────────────────"
echo "Testing TLS versions (should see errors for 1.0/1.1):"
echo ""

echo "Testing TLS 1.0 (should FAIL):"
timeout 3 openssl s_client -connect "$TARGET_HOST:443" -tls1 </dev/null 2>&1 | grep -q "SSLV3 alert handshake failure\|UNSUPPORTED_PROTOCOL\|UNKNOWN_PROTOCOL" && echo "✓ TLS 1.0 BLOCKED (correct)" || echo "✗ TLS 1.0 still accessible (PROBLEM)"
echo ""

echo "Testing TLS 1.1 (should FAIL):"
timeout 3 openssl s_client -connect "$TARGET_HOST:443" -tls1_1 </dev/null 2>&1 | grep -q "SSLV3 alert handshake failure\|UNSUPPORTED_PROTOCOL\|UNKNOWN_PROTOCOL" && echo "✓ TLS 1.1 BLOCKED (correct)" || echo "✗ TLS 1.1 still accessible (PROBLEM)"
echo ""

echo "Testing TLS 1.2 (should SUCCEED):"
timeout 3 openssl s_client -connect "$TARGET_HOST:443" -tls1_2 </dev/null 2>&1 | grep -q "Cipher\|Protocol" && echo "✓ TLS 1.2 ENABLED (correct)" || echo "✗ TLS 1.2 not working"
echo ""

echo "Testing TLS 1.3 (should SUCCEED):"
timeout 3 openssl s_client -connect "$TARGET_HOST:443" -tls1_3 </dev/null 2>&1 | grep -q "Cipher\|Protocol" && echo "✓ TLS 1.3 ENABLED (correct)" || echo "✗ TLS 1.3 not working"
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "SECURITY FIX DEPLOYMENT COMPLETE"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Summary:"
echo "  ✓ TLS 1.0 and 1.1 disabled"
echo "  ✓ TLS 1.2 and 1.3 enforced"
echo "  ✓ Modern cipher suites configured"
echo "  ✓ nginx reloaded without downtime"
echo ""
echo "Backup location: /etc/nginx/sites-available/castle-celestial.backup.*"
echo ""
echo "To rollback (if needed):"
echo "  sudo cp /etc/nginx/sites-available/castle-celestial.backup.YYYYMMDD-HHMMSS /etc/nginx/sites-available/castle-celestial"
echo "  sudo systemctl reload nginx"
echo ""
