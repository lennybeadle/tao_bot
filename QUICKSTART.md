# Quick Start Guide

Get your TAO staking bot running in 5 minutes!

## Step 1: Install Dependencies

```bash
# Python packages
pip install -r requirements.txt

# Frontend packages
cd frontend && npm install && cd ..
```

## Step 2: Configure

```bash
# Copy and edit environment file
cp .env.example .env
```

Edit `.env` and set:
- `WALLET_NAME` - Your Bittensor wallet name
- `WALLET_HOTKEY` - Your hotkey name
- `MONITORED_SUBNETS` - Subnets to watch (e.g., "46,19,8")

## Step 3: Initialize Database

```bash
python init_db.py
```

## Step 4: Start Services

Open 3 terminal windows:

**Terminal 1 - Bot:**
```bash
python start_bot.py
```

**Terminal 2 - API:**
```bash
python start_api.py
```

**Terminal 3 - Frontend:**
```bash
cd frontend
npm run dev
```

## Step 5: Access Dashboard

Open your browser to: `http://localhost:3000`

## What to Expect

1. **Bot starts monitoring** - You'll see logs about mempool monitoring
2. **Dashboard shows stats** - Statistics update every 5 seconds
3. **Trades appear** - When profitable stakes are detected, trades execute

## First Trade

When the bot detects a large wallet stake:
- It calculates if it's profitable
- Stakes before the wallet
- Waits for wallet stake
- Unstakes after

All trades appear in the dashboard!

## Troubleshooting

**Bot not starting?**
- Check wallet name/hotkey in `.env`
- Verify RPC endpoint is accessible

**No trades?**
- Check `MIN_WALLET_STAKE` threshold
- Verify monitored subnets have activity
- Some RPC nodes don't expose mempool

**Frontend not loading?**
- Make sure API server is running on port 8000
- Check browser console for errors

## Next Steps

- Adjust trading parameters in `.env`
- Monitor performance in dashboard
- Review trade history
- Track influential wallets

Happy trading! 🚀
