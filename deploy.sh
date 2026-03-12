#!/bin/bash

# TAO Bot Ubuntu Deployment Script
# This script automates the deployment process

set -e  # Exit on error

echo "========================================="
echo "TAO Staking Bot - Ubuntu Deployment"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

# Configuration
APP_USER="tao_bot"
APP_DIR="/opt/tao_bot"
SERVICE_USER_HOME="/home/$APP_USER"

echo -e "${GREEN}Step 1: Updating system packages...${NC}"
apt update
apt upgrade -y

echo -e "${GREEN}Step 2: Installing system dependencies...${NC}"
apt install -y \
    build-essential \
    curl \
    git \
    pkg-config \
    libssl-dev \
    sqlite3 \
    libsqlite3-dev \
    nginx

echo -e "${GREEN}Step 3: Installing Rust...${NC}"
if ! command -v rustc &> /dev/null; then
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source $HOME/.cargo/env
else
    echo "Rust already installed"
fi

# Add cargo to PATH for root
export PATH="$HOME/.cargo/bin:$PATH"

echo -e "${GREEN}Step 4: Creating application user...${NC}"
if ! id "$APP_USER" &>/dev/null; then
    useradd -r -s /bin/bash -d "$APP_DIR" -m "$APP_USER"
    echo "User $APP_USER created"
else
    echo "User $APP_USER already exists"
fi

echo -e "${GREEN}Step 5: Setting up application directory...${NC}"
mkdir -p "$APP_DIR"
chown "$APP_USER:$APP_USER" "$APP_DIR"

# If running from project directory, copy files
if [ -f "Cargo.toml" ]; then
    echo "Copying project files..."
    cp -r . "$APP_DIR/"
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
fi

echo -e "${GREEN}Step 6: Building the project...${NC}"
cd "$APP_DIR"
sudo -u "$APP_USER" bash << 'EOF'
source $HOME/.cargo/env
export PATH="$HOME/.cargo/bin:$PATH"
cargo build --release
EOF

echo -e "${GREEN}Step 7: Creating .env file template...${NC}"
if [ ! -f "$APP_DIR/.env" ]; then
    cat > "$APP_DIR/.env" << 'ENVEOF'
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
ALLOWED_WALLET_ADDRESSES=
ENVEOF
    chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    echo -e "${YELLOW}Please edit $APP_DIR/.env with your configuration${NC}"
else
    echo ".env file already exists"
fi

echo -e "${GREEN}Step 8: Initializing database...${NC}"
sudo -u "$APP_USER" "$APP_DIR/target/release/init_db" || echo "Database initialization (may fail if already exists)"

echo -e "${GREEN}Step 9: Creating systemd services...${NC}"

# Bot service
cat > /etc/systemd/system/tao-bot.service << 'SERVICEEOF'
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
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
SERVICEEOF

# API service
cat > /etc/systemd/system/tao-api.service << 'SERVICEEOF'
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
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
SERVICEEOF

echo -e "${GREEN}Step 10: Reloading systemd and enabling services...${NC}"
systemctl daemon-reload
systemctl enable tao-bot.service
systemctl enable tao-api.service

echo -e "${GREEN}Step 11: Configuring firewall...${NC}"
if command -v ufw &> /dev/null; then
    ufw allow 8000/tcp comment 'TAO Bot API' || true
    echo "Firewall rule added"
fi

echo ""
echo -e "${GREEN}========================================="
echo "Deployment Complete!"
echo "=========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Edit configuration: sudo nano $APP_DIR/.env"
echo "2. Initialize database: sudo -u $APP_USER $APP_DIR/target/release/init_db"
echo "3. Start services:"
echo "   sudo systemctl start tao-bot"
echo "   sudo systemctl start tao-api"
echo "4. Check status:"
echo "   sudo systemctl status tao-bot"
echo "   sudo systemctl status tao-api"
echo "5. View logs:"
echo "   sudo journalctl -u tao-bot.service -f"
echo "   sudo journalctl -u tao-api.service -f"
echo ""
echo -e "${YELLOW}Remember to configure your .env file before starting services!${NC}"
