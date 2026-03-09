#!/usr/bin/env python3
"""
Initialize the database
"""
import asyncio
from bot.database import init_db, init_default_monitored_subnets

async def main():
    print("Initializing database...")
    await init_db()
    print("Initializing default monitored subnets...")
    await init_default_monitored_subnets()
    print("Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(main())
