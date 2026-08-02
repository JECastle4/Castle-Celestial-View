#!/bin/bash
# MANUAL DEPLOYMENT GUIDE - TLS 1.0/1.1 Security Fix
# Run these commands directly on the production server via SSH

echo "═══════════════════════════════════════════════════════════════"
echo "MANUAL TLS 1.0/1.1 SECURITY FIX DEPLOYMENT"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "SSH to your production server:"
echo "  ssh deployuser@77.68.79.252"
echo ""
echo "Then run the following commands:"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
cat << 'EOF'
# Step 1: Download updated nginx config
cd /tmp
curl -sSL 'https://raw.githubusercontent.com/JECastle4/Castle-Celestial-View/main/scripts/castle-celestial.nginx.conf' -o castle-celestial.new

# Verify file was downloaded
ls -lh castle-celestial.new
echo ""

# Step 2: Backup current configuration
sudo cp /etc/nginx/sites-available/celestial-view /etc/nginx/sites-available/celestial-view.backup.$(date +%Y%m%d-%H%M%S)
echo "✓ Backed up current nginx config"
echo ""

# Step 3: Validate new configuration syntax
sudo cp /tmp/castle-celestial.new /etc/nginx/sites-available/celestial-view
sudo nginx -t

# Check if syntax is valid
if [ $? -eq 0 ]; then
    echo "✓ Configuration syntax is valid"
else
    echo "✗ Configuration has syntax errors!"
    echo "  Restoring backup and exiting..."
    sudo cp /etc/nginx/sites-available/celestial-view.backup.* /etc/nginx/sites-available/celestial-view
    sudo systemctl reload nginx
    exit 1
fi
echo ""

# Step 4: Reload nginx (apply new configuration)
echo "Reloading nginx..."
sudo systemctl reload nginx
echo "✓ nginx reloaded successfully"
echo ""

# Step 5: Verify TLS configuration
echo "Step 5: Verifying TLS Configuration"
echo "════════════════════════════════════"
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

echo "════════════════════════════════════════════════════════════════"
echo "DEPLOYMENT COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Summary:"
echo "  ✓ nginx config updated with TLS 1.2+ enforcement"
echo "  ✓ nginx reloaded (no downtime)"
echo "  ✓ Backup saved to: /etc/nginx/sites-available/celestial-view.backup.*"
echo ""
echo "Rollback (if needed):"
echo "  sudo cp /etc/nginx/sites-available/celestial-view.backup.YYYYMMDD-HHMMSS /etc/nginx/sites-available/celestial-view"
echo "  sudo systemctl reload nginx"
echo ""

EOF

echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "AFTER DEPLOYMENT:"
echo ""
echo "1. Run external pen test from your local machine:"
echo "   bash scripts/external-pen-test-windows.sh"
echo ""
echo "2. Verify TLS 1.0/1.1 are blocked:"
echo "   - Should show: tls1: ✓ NOT supported"
echo "   - Should show: tls1_1: ✓ NOT supported"
echo "   - Should show: tls1_2: ⚠️ SUPPORTED (correct)"
echo "   - Should show: tls1_3: ⚠️ SUPPORTED (correct)"
echo ""
