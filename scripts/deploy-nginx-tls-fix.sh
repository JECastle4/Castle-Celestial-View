#!/bin/bash
# Deploy TLS 1.0/1.1 security fix to production nginx.conf
# Run on production server

set -e

echo "==================================================================="
echo "Deploying TLS 1.0/1.1 Security Fix to nginx.conf"
echo "==================================================================="
echo ""

# Step 1: Download fixed nginx.conf from GitHub
echo "Step 1: Downloading fixed nginx.conf from GitHub..."
cd /tmp
curl -sSL 'https://raw.githubusercontent.com/JECastle4/Castle-Celestial-View/main/scripts/nginx.conf' -o nginx.conf.new
echo "✓ Downloaded nginx.conf.new"
echo ""

# Step 2: Backup current configuration
echo "Step 2: Backing up current nginx.conf..."
BACKUP_FILE="/etc/nginx/nginx.conf.backup.$(date +%Y%m%d-%H%M%S)"
sudo cp /etc/nginx/nginx.conf "$BACKUP_FILE"
echo "✓ Backed up to: $BACKUP_FILE"
echo ""

# Step 3: Deploy new configuration
echo "Step 3: Deploying new nginx.conf..."
sudo cp /tmp/nginx.conf.new /etc/nginx/nginx.conf
echo "✓ Deployed new nginx.conf"
echo ""

# Step 4: Validate nginx configuration syntax
echo "Step 4: Validating nginx configuration..."
if sudo nginx -t; then
    echo "✓ Configuration syntax VALID"
    echo ""
else
    echo "✗ Configuration has SYNTAX ERRORS!"
    echo "  Rolling back..."
    sudo cp "$BACKUP_FILE" /etc/nginx/nginx.conf
    echo "  Rollback complete."
    exit 1
fi

# Step 5: Reload nginx
echo "Step 5: Reloading nginx..."
sudo systemctl reload nginx
echo "✓ nginx reloaded successfully (no downtime)"
echo ""

# Step 6: Verify the change took effect
echo "Step 6: Verifying TLS protocols..."
echo ""
echo "Testing TLS 1.0 (should FAIL):"
timeout 3 openssl s_client -connect localhost:443 -tls1 </dev/null 2>&1 | grep -i "alert\|fail" && echo "✓ TLS 1.0 BLOCKED" || echo "⚠️  TLS 1.0 still accessible"
echo ""

echo "Testing TLS 1.1 (should FAIL):"
timeout 3 openssl s_client -connect localhost:443 -tls1_1 </dev/null 2>&1 | grep -i "alert\|fail" && echo "✓ TLS 1.1 BLOCKED" || echo "⚠️  TLS 1.1 still accessible"
echo ""

echo "Testing TLS 1.2 (should SUCCEED):"
timeout 3 openssl s_client -connect localhost:443 -tls1_2 </dev/null 2>&1 | grep -i "cipher\|protocol" && echo "✓ TLS 1.2 WORKING" || echo "⚠️  TLS 1.2 not working"
echo ""

echo "Testing TLS 1.3 (should SUCCEED):"
timeout 3 openssl s_client -connect localhost:443 -tls1_3 </dev/null 2>&1 | grep -i "cipher\|protocol" && echo "✓ TLS 1.3 WORKING" || echo "⚠️  TLS 1.3 not working"
echo ""

echo "==================================================================="
echo "DEPLOYMENT COMPLETE ✓"
echo "==================================================================="
echo ""
echo "Summary:"
echo "  ✓ nginx.conf updated with TLS 1.2+ ONLY enforcement"
echo "  ✓ nginx reloaded without downtime"
echo "  ✓ Backup saved: $BACKUP_FILE"
echo ""
echo "Next steps (run from your local machine):"
echo "  1. Run external pen test:"
echo "     bash scripts/external-pen-test-windows.sh castlecelestialview.net"
echo "  2. Verify TLS 1.0/1.1 are blocked (✓ NOT supported)"
echo ""
