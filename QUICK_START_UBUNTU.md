# Quick Start Guide - Ubuntu

## Automated Deployment (Recommended)

```bash
# Make script executable
chmod +x deploy.sh

# Run deployment script (as root/sudo)
sudo ./deploy.sh
```

## Manual Deployment

### 1. Install Dependencies

```bash
sudo apt update
sudo apt install -y build-essential curl git pkg-config libssl-dev sqlite3 libsqlite3-dev
```

### 2. Install Rust

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

### 3. Build Project

```bash
cd /path/to/tao_bot
cargo build --release
```

### 4. Configure

```bash
nano .env  # Edit with your settings
```

### 5. Initialize Database

```bash
./target/release/init_db
```

### 6. Run Services

**Terminal 1 - Bot:**
```bash
./target/release/start_bot
```

**Terminal 2 - API:**
```bash
./target/release/start_api
```

## Production Setup with Systemd

### Create Services

Copy the systemd service files from `UBUNTU_DEPLOYMENT.md` or use the deployment script.

### Start Services

```bash
sudo systemctl start tao-bot
sudo systemctl start tao-api
```

### Enable Auto-Start

```bash
sudo systemctl enable tao-bot
sudo systemctl enable tao-api
```

### View Logs

```bash
sudo journalctl -u tao-bot -f
sudo journalctl -u tao-api -f
```

## Common Commands

```bash
# Check status
sudo systemctl status tao-bot
sudo systemctl status tao-api

# Restart services
sudo systemctl restart tao-bot
sudo systemctl restart tao-api

# Stop services
sudo systemctl stop tao-bot
sudo systemctl stop tao-api

# View logs
sudo journalctl -u tao-bot -n 100
sudo journalctl -u tao-api -n 100
```

## Configuration File

Edit `/opt/tao_bot/.env` (or your project directory):

```env
WALLET_NAME=your_wallet
WALLET_HOTKEY=your_hotkey
WALLET_PASSWORD=your_password
SUBTENSOR_RPC=wss://entrypoint-finney.opentensor.ai:443
MONITORED_SUBNETS=46,19,8
API_PORT=8000
```

## Troubleshooting

```bash
# Check if services are running
sudo systemctl status tao-bot tao-api

# Check logs for errors
sudo journalctl -u tao-bot.service --since "1 hour ago"

# Test API
curl http://localhost:8000/api/stats

# Rebuild if needed
cd /opt/tao_bot
cargo build --release
```

For detailed instructions, see `UBUNTU_DEPLOYMENT.md`.
