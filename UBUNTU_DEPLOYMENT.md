# Ubuntu Deployment Guide

Complete guide to deploy and run the TAO Staking Bot on Ubuntu.

## Prerequisites

- Ubuntu 20.04 LTS or later (22.04 LTS recommended)
- Root or sudo access
- At least 2GB RAM
- 10GB free disk space
- Internet connection

## Step 1: System Updates

```bash
sudo apt update
sudo apt upgrade -y
```

## Step 2: Install Required System Dependencies

```bash
sudo apt install -y \
    build-essential \
    curl \
    git \
    pkg-config \
    libssl-dev \
    sqlite3 \
    libsqlite3-dev
```

## Step 3: Install Rust

### Option A: Using rustup (Recommended)

```bash
# Download and run rustup installer
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Add Rust to PATH for current session
source $HOME/.cargo/env

# Verify installation
rustc --version
cargo --version

# Install stable toolchain (if not already installed)
rustup default stable
```

### Option B: Using apt (Alternative)

```bash
sudo apt install -y rustc cargo
```

**Note**: rustup is recommended as it provides better version management.

## Step 4: Clone and Build the Project

```bash
# Navigate to your project directory
cd /opt  # or your preferred location

# Clone the repository (if not already done)
# git clone <your-repo-url> tao_bot
# cd tao_bot

# Or if you already have the project, navigate to it
cd /path/to/tao_bot

# Build the project in release mode
cargo build --release

# This will create binaries in target/release/
# - start_bot
# - start_api
# - init_db
```

**Build time**: First build may take 10-20 minutes. Subsequent builds are faster.

## Step 5: Create Application User (Recommended for Security)

```bash
# Create a dedicated user for the bot
sudo useradd -r -s /bin/false -d /opt/tao_bot tao_bot

# Create application directory
sudo mkdir -p /opt/tao_bot
sudo chown tao_bot:tao_bot /opt/tao_bot

# Copy project files (adjust paths as needed)
sudo cp -r /path/to/your/tao_bot/* /opt/tao_bot/
sudo chown -R tao_bot:tao_bot /opt/tao_bot
```

## Step 6: Configure Environment

```bash
# Navigate to application directory
cd /opt/tao_bot

# Create .env file
sudo -u tao_bot nano .env
```

Add the following configuration (adjust values as needed):

```env
# RPC Configuration
SUBTENSOR_RPC=wss://entrypoint-finney.opentensor.ai:443

# Wallet Configuration
WALLET_NAME=your_wallet_name
WALLET_HOTKEY=your_hotkey_name
WALLET_PASSWORD=your_wallet_password

# Trading Parameters
MIN_WALLET_STAKE=0.001
MAX_BOT_STAKE=100.0
MIN_EXPECTED_PROFIT=0.05
BOT_STAKE_RATIO=0.5
MIN_WALLET_RESERVE=0.02

# Subnets to Monitor
MONITORED_SUBNETS=46,19,8

# Risk Management
MAX_DAILY_TRADES=50
MAX_SLIPPAGE=0.05

# Performance
MEMPOOL_CHECK_INTERVAL=0.05
TRANSACTION_TIMEOUT=30.0
USE_MULTIPLE_RPC=true

# Database
DATABASE_URL=sqlite:./bot.db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Allowed Wallet Addresses (optional, comma-separated)
# Leave empty to allow all wallets
ALLOWED_WALLET_ADDRESSES=
```

Save and exit (Ctrl+X, Y, Enter).

```bash
# Secure the .env file
sudo chmod 600 /opt/tao_bot/.env
sudo chown tao_bot:tao_bot /opt/tao_bot/.env
```

## Step 7: Initialize Database

```bash
# Run as the application user
sudo -u tao_bot /opt/tao_bot/target/release/init_db

# Or if running from project directory
cd /opt/tao_bot
sudo -u tao_bot cargo run --release --bin init_db
```

This creates the SQLite database file `bot.db` in the current directory.

## Step 8: Test Run (Manual)

### Test the Bot

```bash
# Run in foreground to see logs
sudo -u tao_bot /opt/tao_bot/target/release/start_bot

# Or with cargo
cd /opt/tao_bot
sudo -u tao_bot cargo run --release --bin start_bot
```

Press Ctrl+C to stop.

### Test the API Server

In a separate terminal:

```bash
sudo -u tao_bot /opt/tao_bot/target/release/start_api

# Or with cargo
cd /opt/tao_bot
sudo -u tao_bot cargo run --release --bin start_api
```

Test the API:
```bash
curl http://localhost:8000/
curl http://localhost:8000/api/stats
```

## Step 9: Create Systemd Services (Production)

### Create Bot Service

```bash
sudo nano /etc/systemd/system/tao-bot.service
```

Add the following:

```ini
[Unit]
Description=TAO Staking Bot
After=network.target

[Service]
Type=simple
User=tao_bot
Group=tao_bot
WorkingDirectory=/opt/tao_bot
Environment="RUST_LOG=info"
ExecStart=/opt/tao_bot/target/release/start_bot
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### Create API Service

```bash
sudo nano /etc/systemd/system/tao-api.service
```

Add the following:

```ini
[Unit]
Description=TAO Staking Bot API Server
After=network.target

[Service]
Type=simple
User=tao_bot
Group=tao_bot
WorkingDirectory=/opt/tao_bot
Environment="RUST_LOG=info"
ExecStart=/opt/tao_bot/target/release/start_api
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

## Step 10: Enable and Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable tao-bot.service
sudo systemctl enable tao-api.service

# Start services
sudo systemctl start tao-bot.service
sudo systemctl start tao-api.service

# Check status
sudo systemctl status tao-bot.service
sudo systemctl status tao-api.service
```

## Step 11: View Logs

```bash
# View bot logs
sudo journalctl -u tao-bot.service -f

# View API logs
sudo journalctl -u tao-api.service -f

# View last 100 lines
sudo journalctl -u tao-bot.service -n 100

# View logs since today
sudo journalctl -u tao-bot.service --since today
```

## Step 12: Firewall Configuration

```bash
# If using UFW
sudo ufw allow 8000/tcp comment 'TAO Bot API'

# If using firewalld
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

## Step 13: Nginx Reverse Proxy (Optional but Recommended)

If you want to expose the API through Nginx:

```bash
# Install Nginx
sudo apt install -y nginx

# Create Nginx configuration
sudo nano /etc/nginx/sites-available/tao-bot
```

Add:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain or IP

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Enable and restart:

```bash
sudo ln -s /etc/nginx/sites-available/tao-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Step 14: SSL Certificate (Optional)

For HTTPS with Let's Encrypt:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Service Management Commands

```bash
# Start services
sudo systemctl start tao-bot
sudo systemctl start tao-api

# Stop services
sudo systemctl stop tao-bot
sudo systemctl stop tao-api

# Restart services
sudo systemctl restart tao-bot
sudo systemctl restart tao-api

# Check status
sudo systemctl status tao-bot
sudo systemctl status tao-api

# Disable auto-start on boot
sudo systemctl disable tao-bot
sudo systemctl disable tao-api

# Enable auto-start on boot
sudo systemctl enable tao-bot
sudo systemctl enable tao-api
```

## Updating the Bot

```bash
# Stop services
sudo systemctl stop tao-bot
sudo systemctl stop tao-api

# Navigate to project directory
cd /opt/tao_bot

# Pull latest changes (if using git)
# git pull

# Rebuild
cargo build --release

# Start services
sudo systemctl start tao-bot
sudo systemctl start tao-api
```

## Troubleshooting

### Bot won't start

```bash
# Check logs
sudo journalctl -u tao-bot.service -n 50

# Check if database exists
ls -la /opt/tao_bot/bot.db

# Check permissions
ls -la /opt/tao_bot/

# Test manual run
cd /opt/tao_bot
sudo -u tao_bot ./target/release/start_bot
```

### API won't start

```bash
# Check if port is in use
sudo netstat -tulpn | grep 8000

# Check logs
sudo journalctl -u tao-api.service -n 50

# Test manual run
cd /opt/tao_bot
sudo -u tao_bot ./target/release/start_api
```

### Database errors

```bash
# Reinitialize database (WARNING: This will delete existing data)
cd /opt/tao_bot
sudo -u tao_bot rm bot.db
sudo -u tao_bot ./target/release/init_db
```

### Permission errors

```bash
# Fix ownership
sudo chown -R tao_bot:tao_bot /opt/tao_bot

# Fix permissions
sudo chmod 755 /opt/tao_bot
sudo chmod 600 /opt/tao_bot/.env
```

### Build errors

```bash
# Update Rust
rustup update

# Clean and rebuild
cd /opt/tao_bot
cargo clean
cargo build --release
```

### Connection errors

```bash
# Test RPC connection
curl -X POST https://entrypoint-finney.opentensor.ai:443 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"system_health","params":[],"id":1}'

# Check network connectivity
ping entrypoint-finney.opentensor.ai
```

## Performance Optimization

### Increase file descriptor limits

```bash
# Edit limits
sudo nano /etc/security/limits.conf
```

Add:
```
tao_bot soft nofile 65535
tao_bot hard nofile 65535
```

### Optimize SQLite

Add to systemd service `[Service]` section:
```ini
LimitNOFILE=65535
```

## Monitoring

### Check resource usage

```bash
# CPU and memory
top -u tao_bot

# Disk usage
df -h
du -sh /opt/tao_bot/

# Process info
ps aux | grep tao_bot
```

### Set up log rotation

```bash
sudo nano /etc/logrotate.d/tao-bot
```

Add:
```
/var/log/tao-bot/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 tao_bot tao_bot
}
```

## Security Best Practices

1. **Keep system updated**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Use firewall**:
   ```bash
   sudo ufw enable
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   ```

3. **Regular backups**:
   ```bash
   # Backup database
   sudo cp /opt/tao_bot/bot.db /opt/tao_bot/backups/bot_$(date +%Y%m%d).db
   ```

4. **Monitor logs**:
   ```bash
   # Set up log monitoring
   sudo journalctl -u tao-bot.service -f
   ```

5. **Secure .env file**:
   ```bash
   sudo chmod 600 /opt/tao_bot/.env
   ```

## Quick Start Summary

```bash
# 1. Install dependencies
sudo apt update && sudo apt install -y build-essential curl git pkg-config libssl-dev sqlite3 libsqlite3-dev

# 2. Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# 3. Build project
cd /opt/tao_bot
cargo build --release

# 4. Configure
nano .env  # Edit configuration

# 5. Initialize database
./target/release/init_db

# 6. Test run
./target/release/start_bot  # In one terminal
./target/release/start_api   # In another terminal

# 7. Set up systemd services (see Step 9)
# 8. Start services
sudo systemctl start tao-bot
sudo systemctl start tao-api
```

## Support

For issues or questions:
- Check logs: `sudo journalctl -u tao-bot.service -f`
- Review configuration: `cat /opt/tao_bot/.env`
- Verify services: `sudo systemctl status tao-bot tao-api`
