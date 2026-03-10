# Ubuntu Deployment Guide

Complete instructions for deploying and running the TAO Staking Bot on Ubuntu.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [System Setup](#system-setup)
3. [Project Installation](#project-installation)
4. [Configuration](#configuration)
5. [Running the Services](#running-the-services)
6. [Production Deployment](#production-deployment)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- Ubuntu 20.04 LTS or later (recommended: 22.04 LTS)
- At least 2GB RAM
- At least 10GB free disk space
- Stable internet connection
- Bittensor wallet with TAO balance

### Required Software

- Python 3.9 or higher
- Node.js 18.x or higher
- npm (comes with Node.js)
- Git
- pip (Python package manager)
- Virtual environment tools (python3-venv)

## System Setup

### 1. Update System Packages

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Install Python and Development Tools

```bash
sudo apt install -y python3 python3-pip python3-venv python3-dev build-essential
```

Verify Python installation:
```bash
python3 --version  # Should be 3.9 or higher
```

### 3. Install Node.js and npm

#### Option A: Using NodeSource Repository (Recommended)

```bash
# Install Node.js 18.x
curl -fsSL https://deb.nodesource.com/setup_21.7.3 | sudo -E bash -
sudo apt install -y nodejs

# Verify installation
node --version  # Should be 18.x or higher
npm --version
```

#### Option B: Using Ubuntu Repository

```bash
sudo apt install -y nodejs npm
```

### 4. Install Git

```bash
sudo apt install -y git
```

### 5. Install Additional Dependencies

```bash
sudo apt install -y libssl-dev libffi-dev
```

## Project Installation

### 1. Clone or Transfer the Project

**Note:** This repository is private, so you must use SSH to clone it.

#### Set Up SSH Keys (if not already done)

If you don't have SSH keys set up with GitHub:

```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -C "your_email@example.com"
# Press Enter to accept default location
# Optionally set a passphrase for extra security

# Start SSH agent
eval "$(ssh-agent -s)"

# Add SSH key to agent
ssh-add ~/.ssh/id_ed25519

# Display public key to add to GitHub
cat ~/.ssh/id_ed25519.pub
```

Copy the output and add it to your GitHub account:
1. Go to GitHub → Settings → SSH and GPG keys
2. Click "New SSH key"
3. Paste your public key and save

Test SSH connection:
```bash
ssh -T git@github.com
```

#### Clone the Repository

Once SSH is set up, clone the repository:
```bash
cd ~
git clone git@github.com:<your-username>/<repository-name>.git tao_bot
cd tao_bot
```

Replace `<your-username>` and `<repository-name>` with your actual GitHub username and repository name.

If you're transferring files from another machine:
```bash
# On your local machine, compress the project
# Then transfer to Ubuntu server using scp:
# scp -r tao_bot user@ubuntu-server:/home/user/

# On Ubuntu server, extract if needed
cd ~/tao_bot
```

### 2. Create Python Virtual Environment

```bash
cd ~/tao_bot
python3 -m venv venv
source venv/bin/activate
```

**Note:** Always activate the virtual environment before running Python commands:
```bash
source venv/bin/activate
```

### 3. Install Python Dependencies

```bash
# Make sure virtual environment is activated
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

### 5. Initialize Database

```bash
# Make sure virtual environment is activated
python init_db.py
```

## Configuration

### 1. Create Environment File

```bash
# Create .env file from template (if .env.example exists)
# Otherwise, create it manually:
nano .env
```

### 2. Configure Environment Variables

Add the following to your `.env` file:

```bash
# Wallet Configuration (REQUIRED)
WALLET_NAME=your_wallet_name
WALLET_HOTKEY=your_hotkey_name

# RPC Configuration
SUBTENSOR_RPC=wss://entrypoint-finney.opentensor.ai:443

# Trading Parameters
MIN_WALLET_STAKE=30.0
MAX_BOT_STAKE=100.0
MIN_EXPECTED_PROFIT=0.05
BOT_STAKE_RATIO=0.5
MIN_WALLET_RESERVE=0.02

# Monitored Subnets (comma-separated)
MONITORED_SUBNETS=46,19,8

# Risk Management
MAX_DAILY_TRADES=50
MAX_SLIPPAGE=0.05

# Performance Settings
MEMPOOL_CHECK_INTERVAL=0.05
TRANSACTION_TIMEOUT=30.0
USE_MULTIPLE_RPC=true

# Database (SQLite by default)
DATABASE_URL=sqlite+aiosqlite:///./bot.db

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

**Important:** Replace `your_wallet_name` and `your_hotkey_name` with your actual Bittensor wallet credentials.

### 3. Configure Frontend (Optional)

If you need to change the API URL:

```bash
cd frontend
nano .env.local
```

Add:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Running the Services

### Method 1: Manual Execution (Development/Testing)

Open three separate terminal windows or use `tmux`/`screen`:

#### Terminal 1 - Start the Bot

```bash
cd ~/tao_bot
source venv/bin/activate
python start_bot.py
```

#### Terminal 2 - Start the API Server

```bash
cd ~/tao_bot
source venv/bin/activate
python start_api.py
```

#### Terminal 3 - Start the Frontend

```bash
cd ~/tao_bot/frontend
npm run dev
```

### Method 2: Using tmux (Recommended for SSH)

Install tmux:
```bash
sudo apt install -y tmux
```

Start a tmux session:
```bash
tmux new -s tao_bot
```

Split into panes:
```bash
# Split horizontally
Ctrl+b, then "

# Split vertically
Ctrl+b, then %

# Switch between panes: Ctrl+b, then arrow keys
```

Run each service in a separate pane.

Detach from tmux: `Ctrl+b, then d`
Reattach: `tmux attach -t tao_bot`

### Method 3: Using screen

```bash
sudo apt install -y screen

# Start screen session
screen -S tao_bot

# Create windows: Ctrl+a, then c
# Switch windows: Ctrl+a, then n (next) or p (previous)
# Detach: Ctrl+a, then d
# Reattach: screen -r tao_bot
```

## Production Deployment

### 1. Build Frontend for Production

```bash
cd ~/tao_bot/frontend
npm run build
```

### 2. Create Systemd Service Files

Create service files to run the bot and API as system services:

#### Bot Service

```bash
sudo nano /etc/systemd/system/tao-bot.service
```

Add:
```ini
[Unit]
Description=TAO Staking Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/tao_bot
Environment="PATH=/home/your_username/tao_bot/venv/bin"
ExecStart=/home/your_username/tao_bot/venv/bin/python start_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### API Service

```bash
sudo nano /etc/systemd/system/tao-api.service
```

Add:
```ini
[Unit]
Description=TAO Bot API Server
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/tao_bot
Environment="PATH=/home/your_username/tao_bot/venv/bin"
ExecStart=/home/your_username/tao_bot/venv/bin/python start_api.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Frontend Service (using PM2 - recommended)

Install PM2:
```bash
sudo npm install -g pm2
```

Create PM2 ecosystem file:
```bash
cd ~/tao_bot
nano ecosystem.config.js
```

Add:
```javascript
module.exports = {
  apps: [{
    name: 'tao-frontend',
    cwd: '/home/your_username/tao_bot/frontend',
    script: 'npm',
    args: 'start',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production'
    }
  }]
};
```

**Important:** Replace `your_username` with your actual Ubuntu username in all service files.

### 3. Enable and Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable tao-bot.service
sudo systemctl enable tao-api.service

# Start services
sudo systemctl start tao-bot.service
sudo systemctl start tao-api.service

# Start frontend with PM2
cd ~/tao_bot
pm2 start ecosystem.config.js
pm2 save
pm2 startup  # Follow instructions to enable PM2 on boot
```

### 4. Check Service Status

```bash
# Check bot service
sudo systemctl status tao-bot.service

# Check API service
sudo systemctl status tao-api.service

# Check frontend
pm2 status

# View logs
sudo journalctl -u tao-bot.service -f
sudo journalctl -u tao-api.service -f
pm2 logs tao-frontend
```

### 5. Configure Firewall (if needed)

```bash
# Allow API port (8000)
sudo ufw allow 8000/tcp

# Allow frontend port (3000)
sudo ufw allow 3000/tcp

# Enable firewall
sudo ufw enable
```

### 6. Set Up Reverse Proxy (Optional, for production)

Install Nginx:
```bash
sudo apt install -y nginx
```

Create Nginx configuration:
```bash
sudo nano /etc/nginx/sites-available/tao-bot
```

Add:
```nginx
server {
    listen 80;
    server_name your_domain.com;  # or your server IP

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/tao-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Troubleshooting

### Common Issues

#### 1. Python Virtual Environment Not Found

**Problem:** `python: command not found` or wrong Python version

**Solution:**
```bash
# Use python3 explicitly
python3 -m venv venv
source venv/bin/activate
which python  # Should point to venv/bin/python
```

#### 2. Permission Denied Errors

**Problem:** Cannot write to files or directories

**Solution:**
```bash
# Fix ownership
sudo chown -R $USER:$USER ~/tao_bot

# Fix permissions
chmod +x start_bot.py start_api.py
```

#### 3. Port Already in Use

**Problem:** Port 8000 or 3000 already in use

**Solution:**
```bash
# Find process using port
sudo lsof -i :8000
sudo lsof -i :3000

# Kill process (replace PID)
sudo kill -9 <PID>

# Or change port in .env file
```

#### 4. Bot Not Detecting Stakes

**Problem:** Bot runs but doesn't detect any transactions

**Solutions:**
- Check RPC connection: Verify `SUBTENSOR_RPC` in `.env`
- Verify monitored subnets are correct
- Check wallet name and hotkey are correct
- Some RPC nodes don't expose mempool - try different RPC endpoint
- Check logs for errors: `sudo journalctl -u tao-bot.service -n 100`

#### 5. Database Errors

**Problem:** Database initialization fails

**Solution:**
```bash
# Remove old database and reinitialize
rm bot.db
python init_db.py
```

#### 6. Frontend Build Errors

**Problem:** `npm run build` fails

**Solution:**
```bash
# Clear node_modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

#### 7. Service Won't Start

**Problem:** Systemd service fails to start

**Solution:**
```bash
# Check service status
sudo systemctl status tao-bot.service

# Check logs
sudo journalctl -u tao-bot.service -n 50

# Verify paths in service file are correct
# Make sure virtual environment path is correct
```

#### 8. Wallet Connection Issues

**Problem:** Cannot connect to wallet

**Solution:**
- Verify wallet name and hotkey in `.env`
- Ensure Bittensor wallet is properly set up on the system
- Check wallet has sufficient TAO balance
- Verify network connectivity

### Useful Commands

```bash
# View bot logs (if using systemd)
sudo journalctl -u tao-bot.service -f

# View API logs
sudo journalctl -u tao-api.service -f

# Restart services
sudo systemctl restart tao-bot.service
sudo systemctl restart tao-api.service

# Stop services
sudo systemctl stop tao-bot.service
sudo systemctl stop tao-api.service

# PM2 commands
pm2 restart tao-frontend
pm2 stop tao-frontend
pm2 logs tao-frontend

# Check disk space
df -h

# Check memory usage
free -h

# Check running processes
ps aux | grep python
ps aux | grep node
```

## Security Considerations

1. **Firewall:** Only open necessary ports
2. **File Permissions:** Keep `.env` file secure (chmod 600)
3. **User Permissions:** Run services as non-root user
4. **SSL/TLS:** Use HTTPS in production (Let's Encrypt)
5. **Backup:** Regularly backup database and configuration
6. **Monitoring:** Set up log monitoring and alerts

## Maintenance

### Regular Tasks

1. **Update Dependencies:**
```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
cd frontend && npm update && cd ..
```

2. **Backup Database:**
```bash
cp bot.db bot.db.backup.$(date +%Y%m%d)
```

3. **Monitor Logs:**
```bash
# Set up log rotation
sudo logrotate -d /etc/logrotate.d/tao-bot
```

4. **Check System Resources:**
```bash
htop  # or top
df -h
```

## Support

For issues and questions:
- Check logs first: `sudo journalctl -u tao-bot.service -n 100`
- Review configuration in `.env`
- Verify all prerequisites are installed
- Check network connectivity to RPC endpoints

---

**Note:** This bot involves financial risk. Always test with small amounts first and monitor closely.
