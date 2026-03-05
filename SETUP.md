# Setup Guide

## Prerequisites

- Python 3.9+
- Node.js 18+
- Bittensor wallet with TAO

## Installation Steps

### 1. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your settings:
# - WALLET_NAME: Your wallet name
# - WALLET_HOTKEY: Your hotkey name
# - Configure trading parameters
```

### 2. Initialize Database

The database will be automatically created on first run. You can also initialize it manually:

```python
python -c "import asyncio; from bot.database import init_db; asyncio.run(init_db())"
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Copy environment file
cp .env.local.example .env.local

# Edit .env.local if API URL is different
```

## Running the Bot

### Terminal 1: Start the Bot

```bash
python start_bot.py
```

### Terminal 2: Start the API Server

```bash
python start_api.py
```

### Terminal 3: Start the Frontend

```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Configuration

Edit `.env` to configure:

- **Trading Parameters**: Min/max stakes, profit thresholds
- **Monitored Subnets**: Which subnets to watch
- **Risk Limits**: Daily trade limits, slippage tolerance
- **Performance**: Mempool check interval, timeouts

## Testing

Before running with real funds:

1. Start with small `MAX_BOT_STAKE` (e.g., 1 TAO)
2. Monitor the dashboard for a few hours
3. Check that trades are executing correctly
4. Gradually increase stake size

## Troubleshooting

### Bot not detecting stakes

- Check RPC connection: `SUBTENSOR_RPC` in `.env`
- Verify monitored subnets are correct
- Check mempool access (some nodes don't expose pending extrinsics)

### Transactions failing

- Verify wallet has sufficient TAO
- Check wallet name and hotkey are correct
- Ensure network connectivity

### Frontend not connecting

- Verify API server is running on port 8000
- Check `NEXT_PUBLIC_API_URL` in frontend `.env.local`
- Check CORS settings in `bot/api.py`

## Security Notes

- Never commit `.env` file
- Keep wallet credentials secure
- Use separate wallets for testing
- Monitor bot activity regularly
