# TAO Staking Bot

A sophisticated front-running bot for Bittensor subnet staking that detects large wallet stakes, simulates price impact, and executes profitable trades.

## Features

- **Mempool Monitoring**: Detects pending stake transactions before block execution
- **Price Impact Simulation**: Calculates expected profit using bonding curve math
- **Automated Execution**: Stakes before large wallets and unstakes after
- **Risk Management**: Configurable limits and profit thresholds
- **Web Dashboard**: Real-time monitoring and configuration management
- **Wallet Tracking**: Identifies and monitors influential wallets

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

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd tao_bot
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your wallet and trading settings
```

4. Initialize database:
```bash
python init_db.py
```

5. Install frontend dependencies:
```bash
cd frontend
npm install
cp .env.local.example .env.local
```

## Configuration

Edit `.env` file with your settings:

- `WALLET_NAME`: Your Bittensor wallet name
- `WALLET_HOTKEY`: Your hotkey name
- `MIN_WALLET_STAKE`: Minimum stake amount to trigger bot (default: 10 TAO)
- `MAX_BOT_STAKE`: Maximum bot stake per trade (default: 100 TAO)
- `MONITORED_SUBNETS`: Comma-separated subnet IDs to monitor

## Usage

### Start the Bot

```bash
python start_bot.py
```

### Start the API Server (in separate terminal)

```bash
python start_api.py
```

The API will be available at `http://localhost:8000`

### Start the Frontend (in separate terminal)

```bash
cd frontend
npm run dev
```

The dashboard will be available at `http://localhost:3000`

**Note**: Run all three services simultaneously for full functionality.

## Frontend

The frontend dashboard provides:

- Real-time trade monitoring
- Statistics and profit tracking
- Configuration management
- Wallet tracking
- Subnet pool information

## API Endpoints

- `GET /api/trades` - Get recent trades
- `GET /api/stats` - Get bot statistics
- `GET /api/wallets` - Get tracked wallets
- `GET /api/config` - Get bot configuration
- `GET /api/pools` - Get subnet pool states

## How It Works

1. **Detection**: Bot monitors mempool for pending stake transactions
2. **Simulation**: Calculates price impact using bonding curve formula
3. **Decision**: Determines if trade is profitable
4. **Execution**: Stakes before wallet, waits for wallet stake, then unstakes
5. **Tracking**: Records all trades in database

## Risk Warning

⚠️ **This bot involves financial risk. Only use with funds you can afford to lose.**

- Transaction ordering is critical
- Network latency affects profitability
- Market conditions can change rapidly
- Always test with small amounts first

## License

MIT License
