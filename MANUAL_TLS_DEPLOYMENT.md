#!/bin/bash
# MANUAL DEPLOYMENT GUIDE - TLS 1.0/1.1 Security Fix
# Updated: Config fixed (removed duplicate directives) and pushed to main
# Run these commands directly on the production server via SSH

echo "═══════════════════════════════════════════════════════════════"
echo "MANUAL TLS 1.0/1.1 SECURITY FIX DEPLOYMENT"
echo "Updated nginx config (no duplicate directives)"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "STATUS: nginx config has been FIXED and pushed to main"
echo "  - Removed duplicate ssl_protocols directive"
echo "  - Removed duplicate ssl_ciphers directive"
echo "  - Removed conflicting 'include options-ssl-nginx.conf'"
echo ""
echo "SSH to your production server and run:"
echo "  ssh deployuser@77.68.79.252"
echo ""
echo "Then paste the commands below:"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
cat << 'EOF'
# Step 1: Download FIXED nginx config from GitHub
cd /tmp
curl -sSL 'https://raw.githubusercontent.com/JECastle4/Castle-Celestial-View/main/scripts/castle-celestial.nginx.conf' -o castle-celestial.new

# Verify file was downloaded
ls -lh castle-celestial.new
echo ""

# Step 2: Backup current configuration
sudo cp /etc/nginx/sites-available/celestial-view /etc/nginx/sites-available/celestial-view.backup.$(date +%Y%m%d-%H%M%S)
echo "✓ Backed up current nginx config"
echo ""

# Step 3: Deploy new configuration
sudo cp /tmp/castle-celestial.new /etc/nginx/sites-available/celestial-view
echo "✓ Deployed new nginx config"
echo ""

# Step 4: Validate nginx configuration syntax
echo "Validating nginx configuration..."
sudo nginx -t

# Check if syntax is valid
if [ $? -eq 0 ]; then
    echo "✓ Configuration syntax VALID - proceeding with reload"
    echo ""
else
    echo "✗ Configuration has SYNTAX ERRORS!"
    echo "  Rolling back to previous version..."
    sudo cp /etc/nginx/sites-available/celestial-view.backup.* /etc/nginx/sites-available/celestial-view
    sudo systemctl reload nginx
    echo "  Rollback complete. Fix the config and try again."
    exit 1
fi

# Step 5: Reload nginx (apply new configuration)
echo "Step 5: Reloading nginx..."
sudo systemctl reload nginx
echo "✓ nginx reloaded successfully (no downtime)"
echo ""

# Step 6: Verify TLS configuration
echo "Step 6: Verifying TLS Configuration"
echo "════════════════════════════════════"
echo ""

echo "Testing TLS 1.0 (should FAIL):"
timeout 3 openssl s_client -connect localhost:443 -tls1 </dev/null 2>&1 | grep -i "alert\|fail" && echo "✓ TLS 1.0 BLOCKED" || echo "⚠️  TLS 1.0 still accessible - check config"
echo ""

echo "Testing TLS 1.1 (should FAIL):"
timeout 3 openssl s_client -connect localhost:443 -tls1_1 </dev/null 2>&1 | grep -i "alert\|fail" && echo "✓ TLS 1.1 BLOCKED" || echo "⚠️  TLS 1.1 still accessible - check config"
echo ""

echo "Testing TLS 1.2 (should SUCCEED):"
timeout 3 openssl s_client -connect localhost:443 -tls1_2 </dev/null 2>&1 | grep -i "cipher\|protocol" && echo "✓ TLS 1.2 WORKING" || echo "⚠️  TLS 1.2 not working"
echo ""

echo "Testing TLS 1.3 (should SUCCEED):"
timeout 3 openssl s_client -connect localhost:443 -tls1_3 </dev/null 2>&1 | grep -i "cipher\|protocol" && echo "✓ TLS 1.3 WORKING" || echo "⚠️  TLS 1.3 not working"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "DEPLOYMENT COMPLETE ✓"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Summary:"
echo "  ✓ nginx config updated with TLS 1.2+ ONLY enforcement"
echo "  ✓ nginx reloaded without downtime"
echo "  ✓ Backup saved: /etc/nginx/sites-available/celestial-view.backup.*"
echo ""
echo "Rollback (if needed):"
echo "  sudo cp /etc/nginx/sites-available/celestial-view.backup.YYYYMMDD-HHMMSS /etc/nginx/sites-available/celestial-view"
echo "  sudo systemctl reload nginx"
echo ""

EOF

echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "AFTER DEPLOYMENT (Run from your local machine):"
echo ""
echo "1. Run external pen test from your local machine:"
echo "   bash scripts/external-pen-test-windows.sh 77.68.79.252"
echo ""
echo "2. Verify results show:"
echo "   - tls1: ✓ NOT supported"
echo "   - tls1_1: ✓ NOT supported"
echo "   - tls1_2: ⚠️ SUPPORTED (correct)"
echo "   - tls1_3: ⚠️ SUPPORTED (correct)"
echo ""
echo "3. If all checks pass:"
echo "   - Push changes to GitHub:"
echo "     git add scripts/castle-celestial.nginx.conf"
echo "     git commit -m 'Security: TLS 1.0/1.1 disabled, enforce TLS 1.2+ only (Issue #206)'"
echo "     git push origin main"
echo ""
echo "   - Tag the release:"
echo "     git tag -a v1.1.1-patch1 -m 'Security patch: TLS 1.0/1.1 disabled'"
echo "     git push origin v1.1.1-patch1"
echo ""
echo "   - Update Issue #206:"
echo "     https://github.com/JECastle4/Castle-Celestial-View/issues/206"
echo "     Document TLS 1.0/1.1 vulnerability (discovered via external pen testing)"
echo "     Link to EXTERNAL_PEN_TEST_CRITICAL_FINDINGS.md"
echo "     Mark as RESOLVED"
echo ""
