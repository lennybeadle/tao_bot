#!/usr/bin/env python3
"""
Start the API server
"""
import uvicorn
from bot.api import app
from bot.config import config
from bot.database import init_db
import asyncio

async def setup():
    """Initialize database before starting server"""
    await init_db()

if __name__ == "__main__":
    asyncio.run(setup())
    uvicorn.run(
        app,
        host=config.api_host,
        port=config.api_port,
        log_level="info"
    )
