"""
Database connection and session management
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import select, delete
from typing import List
from bot.config import config
from bot.models import Base, MonitoredSubnet, Wallet

# Create async engine
engine = create_async_engine(
    config.database_url,
    echo=False,
    future=True
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_monitored_subnets() -> List[int]:
    """Get list of monitored subnet IDs from database"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(MonitoredSubnet.subnet_id))
            subnets = result.scalars().all()
            return list(subnets) if subnets else []
    except Exception as e:
        # If table doesn't exist yet or error, return empty list
        # Fallback to config will be handled by config.py
        return []


async def set_monitored_subnets(subnet_ids: List[int]):
    """Update monitored subnets in database"""
    async with AsyncSessionLocal() as session:
        try:
            # Delete all existing
            result = await session.execute(select(MonitoredSubnet))
            existing = result.scalars().all()
            for item in existing:
                await session.delete(item)
            
            # Add new ones
            for subnet_id in subnet_ids:
                monitored = MonitoredSubnet(subnet_id=subnet_id)
                session.add(monitored)
            
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise


async def init_default_monitored_subnets():
    """Initialize default monitored subnets from config if database is empty"""
    try:
        existing = await get_monitored_subnets()
        if not existing:
            # Use default from config or env
            default_subnets = [int(x) for x in os.getenv("MONITORED_SUBNETS", "46,19,8").split(",")]
            await set_monitored_subnets(default_subnets)
    except Exception:
        # If there's an error, just continue - defaults will be used
        pass


async def get_allowed_wallet_addresses() -> List[str]:
    """Get list of allowed wallet addresses from database"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Wallet.address).where(Wallet.is_allowed == True)
            )
            addresses = result.scalars().all()
            return list(addresses) if addresses else []
    except Exception as e:
        # If table doesn't exist yet or error, return empty list
        return []


async def set_wallet_allowed(address: str, is_allowed: bool = True):
    """Set wallet allowed status - creates wallet if it doesn't exist"""
    async with AsyncSessionLocal() as session:
        try:
            # Try to find existing wallet
            result = await session.execute(
                select(Wallet).where(Wallet.address == address)
            )
            wallet = result.scalar_one_or_none()
            
            if wallet:
                # Update existing wallet
                wallet.is_allowed = is_allowed
            else:
                # Create new wallet with is_allowed set
                wallet = Wallet(address=address, is_allowed=is_allowed)
                session.add(wallet)
            
            await session.commit()
            return wallet
        except Exception as e:
            await session.rollback()
            raise
