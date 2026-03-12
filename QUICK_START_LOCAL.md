# Quick Start - Local Run

## Prerequisites
- Rust installed: https://rustup.rs/
- SQLite3 (usually included)

## Setup (One Time)

```bash
# 1. Build the project
cargo build --release

# 2. Create .env file (copy from .env.example or create manually)
# Edit .env with your wallet credentials

# 3. Initialize database
cargo run --release --bin init_db
```

## Running

### Windows (PowerShell)

**Terminal 1:**
```powershell
.\start_bot.ps1
# Or: cargo run --release --bin start_bot
```

**Terminal 2:**
```powershell
.\start_api.ps1
# Or: cargo run --release --bin start_api
```

### macOS/Linux

**Terminal 1:**
```bash
chmod +x start_bot.sh
./start_bot.sh
# Or: cargo run --release --bin start_bot
```

**Terminal 2:**
```bash
chmod +x start_api.sh
./start_api.sh
# Or: cargo run --release --bin start_api
```

## Verify

- Bot logs: Check terminal output
- API: http://localhost:8000
- Stats: http://localhost:8000/api/stats

## Stop

Press `Ctrl+C` in each terminal

## Troubleshooting

```bash
# Rebuild if needed
cargo clean
cargo build --release

# Reset database
rm bot.db  # or del bot.db on Windows
cargo run --release --bin init_db
```

For detailed instructions, see `LOCAL_RUN_GUIDE.md`
