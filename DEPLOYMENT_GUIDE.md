# Production Deployment Guide

This guide explains how to set up automated deployment of Castle Celestial View releases to your production server.

---

## Overview

The deployment automation consists of two scripts:

- **`verify-production-release.sh`** — Locally verifies a release works before deployment
- **`deploy-production-release.sh`** — Deploys a release to production (requires sudo, systemd, and configuration)

---

## Prerequisites

### System Requirements

- **Linux server** with systemd (Ubuntu 20.04 LTS or later recommended)
- **Root/sudo access** on the server
- **Git** (for cloning the repository)
- **Python 3.9+** (3.14 preferred, matches the wheel)
- **Node.js 20.19.0+** (for frontend)
- **curl, unzip** (included in most Linux distributions)

### GitHub Access

For automated downloads, set a GitHub token:

```bash
# Generate a token at https://github.com/settings/tokens (no scopes needed for public repos)
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
```

---

## Step 1: Set Up Systemd Service

The deployment script expects a systemd service for gunicorn:
- `castle-celestial-api` — Python API service (gunicorn)

The service configuration is included in the repository at `scripts/castle-celestial-api.service`.

### Option A: Download from Repository (Recommended)

On your production server:

```bash
# Download the service file from the repository
sudo curl -fsSL https://raw.githubusercontent.com/JECastle4/Castle-Celestial-View/main/scripts/castle-celestial-api.service \
  -o /etc/systemd/system/castle-celestial-api.service

# Or if using a different default branch/fork, adjust the URL accordingly

# Reload systemd, enable, and start
sudo systemctl daemon-reload
sudo systemctl enable castle-celestial-api
sudo systemctl start castle-celestial-api

# Verify it's running
sudo systemctl status castle-celestial-api
```

### Option B: Manual Setup

Create `/etc/systemd/system/castle-celestial-api.service` with this content:

```ini
[Unit]
Description=Castle Celestial View API (Gunicorn)
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/home/deployuser
ExecStart=/home/deployuser/venv/bin/gunicorn -k uvicorn.workers.UvicornWorker api.main:app --bind 127.0.0.1:8000
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Then enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable castle-celestial-api
sudo systemctl start castle-celestial-api

# Verify it's running
sudo systemctl status castle-celestial-api
```

**Note:** The frontend is served as static files by nginx from `/home/deployuser/dist`, so no separate frontend service is needed.

---

## Step 2: Configure the Deployment Script

Edit `scripts/deploy-production-release.sh` and update these variables at the top to match your server:

```bash
# Systemd service name (no changes needed if using the provided service file)
SERVICE_API="castle-celestial-api"

# Deployment user and directories (must match your setup)
DEPLOY_USER="deployuser"
API_VENV_DIR="/home/deployuser/venv"
FE_INSTALL_DIR="/home/deployuser/dist"

# nginx is automatically reloaded after frontend update
NGINX_RELOAD=true
```

---

## Step 2: Set Up Directory Structure and Permissions

```bash
# Create/ensure venv directory exists and is owned by www-data
sudo chown -R www-data:www-data /home/deployuser/venv

# Create/ensure frontend dist directory exists and is owned by www-data
sudo chown -R www-data:www-data /home/deployuser/dist

# Verify nginx has read access
sudo chmod -R o+rx /home/deployuser/dist
```

---

## Step 4: Test the Deployment Script Locally (Dry-Run)

Before deploying to production, test the script on your development machine:

```bash
# Dry-run: shows what would happen without making changes
./scripts/deploy-production-release.sh v1.1.0.3 --dry-run

# Verify your last release was successful
./scripts/verify-production-release.sh v1.1.0.3
```

---

## Step 5: Deploy to Production

### Recommended Workflow

1. **Set up the server (first time only):**
   ```bash
   # SSH into your production server
   ssh user@castlecelestialview.net
   
   # Update system packages
   sudo apt update && sudo apt upgrade
   
   # Download and install the systemd service file from the repo
   sudo curl -fsSL https://raw.githubusercontent.com/JECastle4/Castle-Celestial-View/main/scripts/castle-celestial-api.service \
     -o /etc/systemd/system/castle-celestial-api.service
   
   # Enable and start the service
   sudo systemctl daemon-reload
   sudo systemctl enable castle-celestial-api
   sudo systemctl start castle-celestial-api
   
   # Verify it's running
   sudo systemctl status castle-celestial-api
   ```

2. **Prepare for deployment:**
   ```bash
   # Adjust directory permissions
   sudo chown -R www-data:www-data /home/deployuser/venv
   sudo chown -R www-data:www-data /home/deployuser/dist
   sudo chmod -R o+rx /home/deployuser/dist
   
   # (optional) Reboot after system updates
   sudo reboot
   ```

3. **Download the deployment script to the server:**
   ```bash
   cd /home/deployuser
   wget https://raw.githubusercontent.com/JECastle4/Castle-Celestial-View/main/scripts/deploy-production-release.sh
   chmod +x deploy-production-release.sh
   ```

4. **Run the deployment (with dry-run first):**
   ```bash
   # Test without making changes
   sudo ./deploy-production-release.sh v1.1.0.3 --dry-run
   
   # Review the output carefully!
   # Then deploy for real:
   sudo ./deploy-production-release.sh v1.1.0.3
   ```

5. **Verify the deployment:**
   ```bash
   # Check services are running
   sudo systemctl status castle-celestial-api
   sudo systemctl status nginx
   
   # Check API is responding
   curl http://localhost:8000/api/health
   
   # Check frontend is serving
   curl http://localhost:80/
   ```

6. **Reboot if needed:**
   ```bash
   # If kernel or critical system packages were updated
   sudo reboot
   ```

---

## Monitoring Deployments

### Check Service Status

```bash
# Quick status
systemctl status castle-celestial-api
systemctl status castle-celestial-frontend

# Follow logs in real-time
journalctl -u castle-celestial-api -f
journalctl -u castle-celestial-frontend -f

# See last N lines of logs
journalctl -u castle-celestial-api -n 50
journalctl -u castle-celestial-frontend -n 50
```

### Access the Application

- **Frontend:** `http://your-domain` or `http://your-ip`
- **API:** `http://your-domain/api` or `http://your-ip:8000`

---

## Troubleshooting

### Services fail to start after deployment

```bash
# Check the error logs
sudo journalctl -u castle-celestial-api -n 50 --no-pager

# Try restarting manually
sudo systemctl restart castle-celestial-api

# If there's a Python error, try reinstalling the wheel
cd /opt/castle-celestial
sudo /opt/castle-celestial/venv/bin/pip install --upgrade --force-reinstall /path/to/wheel.whl
```

### Ports already in use

The script checks if ports are free before starting. If deployment fails:

```bash
# Find what's using port 8000 or 80
sudo lsof -i :8000
sudo lsof -i :80

# Kill the conflicting process (carefully!)
sudo kill -9 <PID>
```

### Restore a backup

If deployment goes wrong, backups are saved at `/opt/castle-celestial/backups/`:

```bash
# List backups
ls -la /opt/castle-celestial/backups/

# Restore from backup (manual for now)
sudo systemctl stop castle-celestial-api castle-celestial-frontend
sudo rm -rf /opt/castle-celestial/api /opt/castle-celestial/frontend
sudo cp -r /opt/castle-celestial/backups/backup-v1.0.0-20260731-123456/api /opt/castle-celestial/
sudo cp -r /opt/castle-celestial/backups/backup-v1.0.0-20260731-123456/frontend /opt/castle-celestial/
sudo systemctl start castle-celestial-api castle-celestial-frontend
```

---

## Script Usage Reference

### Full Syntax

```bash
sudo ./scripts/deploy-production-release.sh <tag> [options]
```

### Options

| Option | Description |
|--------|-------------|
| `<tag>` | **Required.** Git tag to deploy (e.g., `v1.1.0.3`) |
| `--dry-run` | Show what would happen without making changes |
| `--skip-backup` | Don't create a backup before deployment |
| `--verbose` | Enable verbose debug output |
| `--help` | Show help message |

### Examples

```bash
# Standard deployment with backup
sudo ./deploy-production-release.sh v1.1.0.3

# Dry-run to verify configuration
sudo ./deploy-production-release.sh v1.1.0.3 --dry-run

# Deployment with verbose output (useful for debugging)
sudo ./deploy-production-release.sh v1.1.0.3 --verbose

# Skip backup (not recommended, but faster for non-critical updates)
sudo ./deploy-production-release.sh v1.1.0.3 --skip-backup
```

---

## Automation Tips

### Run deployment from a cron job (optional)

You can schedule automatic deployments by creating a cron job:

```bash
# Edit root crontab
sudo crontab -e

# Add a line to deploy weekly (e.g., Sundays at 2 AM)
0 2 * * 0 /opt/castle-celestial/deploy-production-release.sh v1.1.0.3 >> /var/log/ccv-deploy.log 2>&1
```

### Set up deployment notifications

Modify the script or add a wrapper to send notifications:

```bash
#!/bin/bash
# deploy-with-notifications.sh

if sudo /opt/castle-celestial/deploy-production-release.sh v1.1.0.3; then
    echo "Deployment successful" | mail -s "CCV Deployment Success" ops@example.com
else
    echo "Deployment failed" | mail -s "CCV Deployment FAILED" ops@example.com
    exit 1
fi
```

---

## Next Steps

1. ✅ Create systemd service files (`.service` files)
2. ✅ Configure `deploy-production-release.sh` with your paths
3. ✅ Test locally with `--dry-run`
4. ✅ Set up on production server
5. ✅ Run first deployment
6. ✅ Verify application is working
7. ✅ Monitor logs for any issues

For questions or issues, check the script's inline comments or run `./scripts/deploy-production-release.sh --help`.
