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

logger = logging.getLogger(__name__)

async def main():
    bot = TradingBot()
    
    try:
        await bot.initialize()
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        await bot.stop()
    except asyncio.CancelledError:
        logger.info("Task cancelled, shutting down...")
        await bot.stop()
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        await bot.stop()
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown complete")
