#!/usr/bin/env python3
"""
Start the TAO staking bot
"""
import asyncio
import logging
from bot.trading_bot import TradingBot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    bot = TradingBot()
    await bot.initialize()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
