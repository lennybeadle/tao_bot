# TAO Staking Bot (Rust)

A high-performance front-running bot for Bittensor subnet staking, rewritten in Rust for maximum speed and reliability.

## Features

- **Mempool Monitoring**: Detects pending stake transactions before block execution
- **Price Impact Simulation**: Calculates expected profit using bonding curve math
- **Automated Execution**: Stakes before large wallets and unstakes after
- **Risk Management**: Configurable limits and profit thresholds
- **Web Dashboard**: Real-time monitoring and configuration management
- **Wallet Tracking**: Identifies and monitors influential wallets

## Requirements

- Rust 1.70+ (with `cargo`)
- SQLite3
- Access to Bittensor network (Finney)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd tao_bot
```

2. Build the project:
```bash
cargo build --release
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your wallet and trading settings
```

4. Initialize database:
```bash
cargo run --bin init_db
```

## Configuration

Edit `.env` file with your settings:

- `WALLET_NAME`: Your Bittensor wallet name
- `WALLET_HOTKEY`: Your hotkey name
- `WALLET_PASSWORD`: Your wallet password
- `MIN_WALLET_STAKE`: Minimum stake amount to trigger bot (default: 0.001 TAO)
- `MAX_BOT_STAKE`: Maximum bot stake per trade (default: 100.0 TAO)
- `MONITORED_SUBNETS`: Comma-separated subnet IDs to monitor (default: 46,19,8)
- `SUBTENSOR_RPC`: RPC endpoint URL (default: wss://entrypoint-finney.opentensor.ai:443)
- `API_HOST`: API server host (default: 0.0.0.0)
- `API_PORT`: API server port (default: 8000)

## Usage

### Start the Bot

```bash
cargo run --release --bin start_bot
```

### Start the API Server (in separate terminal)

```bash
cargo run --release --bin start_api
```

The API will be available at `http://localhost:8000`

### Start the Frontend (in separate terminal)

```bash
cd frontend
npm install
npm run dev
```

The dashboard will be available at `http://localhost:3000`

**Note**: Run all three services simultaneously for full functionality.

## API Endpoints

- `GET /api/trades` - Get recent trades
- `GET /api/stats` - Get bot statistics
- `GET /api/wallets` - Get tracked wallets
- `GET /api/config` - Get bot configuration
- `PUT /api/config/monitored-subnets` - Update monitored subnets
- `GET /api/pools` - Get subnet pool states
- `PUT /api/wallets/allowed` - Set wallet allowed status

## Performance

The Rust implementation provides:
- **Lower latency**: Native performance without Python interpreter overhead
- **Better concurrency**: Efficient async/await with Tokio
- **Memory safety**: Rust's ownership system prevents common bugs
- **Type safety**: Compile-time guarantees reduce runtime errors

## Architecture

```
┌─────────────────┐
│  Mempool        │
│  Listener       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Price          │
│  Simulator      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Execution      │
│  Engine         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Database       │
│  & API          │
└─────────────────┘
```

## Development

### Running Tests

```bash
cargo test
```

### Building for Production

```bash
cargo build --release
```

The binaries will be in `target/release/`:
- `start_bot` - Main trading bot
- `start_api` - API server
- `init_db` - Database initialization

## Migration from Python

This Rust version maintains API compatibility with the Python version, so the frontend should work without changes. The database schema is identical, so existing databases can be used directly.

## Risk Warning

⚠️ **This bot involves financial risk. Only use with funds you can afford to lose.**

- Transaction ordering is critical
- Network latency affects profitability
- Market conditions can change rapidly
- Always test with small amounts first

## License

MIT License
