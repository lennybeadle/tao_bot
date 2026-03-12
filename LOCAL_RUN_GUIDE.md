# Local Development & Running Guide

Guide to run the TAO Staking Bot on your local machine (Windows, macOS, or Linux).

## Prerequisites

- Rust 1.70+ installed
- SQLite3 (usually comes with the OS or Rust toolchain)
- Internet connection for RPC endpoints

## Step 1: Install Rust

### Windows

1. Download and run the installer from: https://rustup.rs/
2. Or use PowerShell:
   ```powershell
   # Download and run rustup-init
   Invoke-WebRequest -Uri "https://win.rustup.rs/x86_64" -OutFile "rustup-init.exe"
   .\rustup-init.exe
   ```
3. Follow the installer prompts (defaults are usually fine)
4. Restart your terminal/PowerShell after installation

### macOS

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

### Linux (Ubuntu/Debian)

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

### Verify Installation

```bash
rustc --version
cargo --version
```

## Step 2: Clone/Navigate to Project

```bash
# If cloning from repository
git clone <repository-url>
cd tao_bot

# Or if you already have the project
cd /path/to/tao_bot
```

## Step 3: Build the Project

```bash
# Build in debug mode (faster, for development)
cargo build

# Or build in release mode (optimized, for production)
cargo build --release
```

**Note**: First build may take 10-20 minutes. Subsequent builds are much faster.

## Step 4: Configure Environment

Create a `.env` file in the project root:

### Windows (PowerShell)

```powershell
# Create .env file
@"
SUBTENSOR_RPC=wss://entrypoint-finney.opentensor.ai:443
WALLET_NAME=your_wallet_name
WALLET_HOTKEY=your_hotkey_name
WALLET_PASSWORD=your_wallet_password
MIN_WALLET_STAKE=0.001
MAX_BOT_STAKE=100.0
MIN_EXPECTED_PROFIT=0.05
BOT_STAKE_RATIO=0.5
MIN_WALLET_RESERVE=0.02
MONITORED_SUBNETS=46,19,8
MAX_DAILY_TRADES=50
MAX_SLIPPAGE=0.05
MEMPOOL_CHECK_INTERVAL=0.05
TRANSACTION_TIMEOUT=30.0
USE_MULTIPLE_RPC=true
DATABASE_URL=sqlite:./bot.db
API_HOST=0.0.0.0
API_PORT=8000
ALLOWED_WALLET_ADDRESSES=
"@ | Out-File -FilePath .env -Encoding utf8
```

### macOS/Linux

```bash
cat > .env << 'EOF'
SUBTENSOR_RPC=wss://entrypoint-finney.opentensor.ai:443
WALLET_NAME=your_wallet_name
WALLET_HOTKEY=your_hotkey_name
WALLET_PASSWORD=your_wallet_password
MIN_WALLET_STAKE=0.001
MAX_BOT_STAKE=100.0
MIN_EXPECTED_PROFIT=0.05
BOT_STAKE_RATIO=0.5
MIN_WALLET_RESERVE=0.02
MONITORED_SUBNETS=46,19,8
MAX_DAILY_TRADES=50
MAX_SLIPPAGE=0.05
MEMPOOL_CHECK_INTERVAL=0.05
TRANSACTION_TIMEOUT=30.0
USE_MULTIPLE_RPC=true
DATABASE_URL=sqlite:./bot.db
API_HOST=0.0.0.0
API_PORT=8000
ALLOWED_WALLET_ADDRESSES=
EOF
```

**Important**: Edit the `.env` file and replace placeholder values with your actual configuration:
- `WALLET_NAME`: Your Bittensor wallet name
- `WALLET_HOTKEY`: Your hotkey name  
- `WALLET_PASSWORD`: Your wallet password

## Step 5: Initialize Database

```bash
# Debug build
cargo run --bin init_db

# Release build
cargo run --release --bin init_db
```

This creates the `bot.db` SQLite database file in the project directory.

## Step 6: Run the Bot

### Option A: Run Both Services Separately

**Terminal 1 - Start the Bot:**

```bash
# Debug mode
cargo run --bin start_bot

# Release mode (recommended)
cargo run --release --bin start_bot
```

**Terminal 2 - Start the API Server:**

```bash
# Debug mode
cargo run --bin start_api

# Release mode (recommended)
cargo run --release --bin start_api
```

### Option B: Run Directly from Binary (After Building)

**Terminal 1 - Bot:**
```bash
# Windows
.\target\release\start_bot.exe

# macOS/Linux
./target/release/start_bot
```

**Terminal 2 - API:**
```bash
# Windows
.\target\release\start_api.exe

# macOS/Linux
./target/release/start_api
```

## Step 7: Verify It's Working

### Check Bot Logs

You should see output like:
```
INFO tao_bot::trading_bot: Initializing trading bot...
INFO tao_bot::trading_bot: Successfully connected to Bittensor network
INFO tao_bot::mempool_listener: Connected to wss://...
INFO tao_bot::mempool_listener: Mempool listener started with 2 nodes
```

### Test API

Open a new terminal and test the API:

```bash
# Windows PowerShell
Invoke-WebRequest -Uri "http://localhost:8000/" | Select-Object -ExpandProperty Content

# macOS/Linux
curl http://localhost:8000/

# Test stats endpoint
curl http://localhost:8000/api/stats
```

Or open in browser: http://localhost:8000/

### Check Database

```bash
# Windows (if sqlite3 is installed)
sqlite3 bot.db "SELECT COUNT(*) FROM trades;"

# macOS/Linux
sqlite3 bot.db "SELECT COUNT(*) FROM trades;"
```

## Running with Custom Log Level

Set the `RUST_LOG` environment variable for more detailed logs:

### Windows PowerShell

```powershell
$env:RUST_LOG="debug"
cargo run --release --bin start_bot
```

### Windows CMD

```cmd
set RUST_LOG=debug
cargo run --release --bin start_bot
```

### macOS/Linux

```bash
RUST_LOG=debug cargo run --release --bin start_bot
```

Log levels: `error`, `warn`, `info`, `debug`, `trace`

## Troubleshooting

### Build Errors

```bash
# Update Rust
rustup update

# Clean and rebuild
cargo clean
cargo build --release
```

### Database Errors

```bash
# Delete and recreate database
rm bot.db  # or del bot.db on Windows
cargo run --release --bin init_db
```

### Port Already in Use

If port 8000 is already in use:

1. Change `API_PORT` in `.env` file
2. Or find and kill the process:

**Windows:**
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

**macOS/Linux:**
```bash
# Find process
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Connection Errors

If you see connection errors:

1. Check your internet connection
2. Verify RPC endpoint is accessible:
   ```bash
   # Test WebSocket connection (may need special tools)
   curl -I https://entrypoint-finney.opentensor.ai:443
   ```
3. Try different RPC endpoints in `.env`:
   ```
   SUBTENSOR_RPC=wss://archivelb-finney.opentensor.ai:443
   ```

### Permission Errors (Linux/macOS)

```bash
# Make binaries executable
chmod +x target/release/start_bot
chmod +x target/release/start_api
chmod +x target/release/init_db
```

## Development Mode

For development with hot-reloading and better error messages:

```bash
# Run in debug mode with detailed logs
RUST_LOG=debug cargo run --bin start_bot

# Enable backtraces for better error messages
RUST_BACKTRACE=1 cargo run --bin start_bot
```

## Quick Start Scripts

### Windows (start_bot.ps1)

Create `start_bot.ps1`:
```powershell
$env:RUST_LOG="info"
cargo run --release --bin start_bot
```

Create `start_api.ps1`:
```powershell
$env:RUST_LOG="info"
cargo run --release --bin start_api
```

Run:
```powershell
.\start_bot.ps1    # In one terminal
.\start_api.ps1    # In another terminal
```

### macOS/Linux (start_bot.sh)

Create `start_bot.sh`:
```bash
#!/bin/bash
export RUST_LOG=info
cargo run --release --bin start_bot
```

Create `start_api.sh`:
```bash
#!/bin/bash
export RUST_LOG=info
cargo run --release --bin start_api
```

Make executable and run:
```bash
chmod +x start_bot.sh start_api.sh
./start_bot.sh    # In one terminal
./start_api.sh    # In another terminal
```

## Stopping the Bot

Press `Ctrl+C` in the terminal where the bot is running.

## Next Steps

1. **Monitor Logs**: Watch the console output for bot activity
2. **Check API**: Visit http://localhost:8000/api/stats to see statistics
3. **View Trades**: Check http://localhost:8000/api/trades for executed trades
4. **Configure**: Adjust settings in `.env` file as needed

## Frontend (Optional)

If you have the frontend:

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at http://localhost:3000

## Production vs Development

- **Development**: Use `cargo run` (debug mode, faster compilation, slower runtime)
- **Production**: Use `cargo run --release` (optimized, slower compilation, faster runtime)

For local testing, either works, but release mode is recommended for better performance.
