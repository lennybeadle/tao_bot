"""
Database models for tracking trades and wallets
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Trade(Base):
    """Track executed trades"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Trade details
    subnet_id = Column(Integer, index=True)
    wallet_address = Column(String, index=True)
    wallet_stake = Column(Float)
    bot_stake = Column(Float)
    
    # Price information
    price_before = Column(Float)
    price_after = Column(Float)
    expected_profit = Column(Float)
    actual_profit = Column(Float, nullable=True)
    
    # Transaction hashes
    bot_stake_tx = Column(String, nullable=True)
    bot_unstake_tx = Column(String, nullable=True)
    wallet_tx = Column(String, nullable=True)
    
    # Status
    status = Column(String, default="pending")  # pending, executed, failed, completed
    error_message = Column(Text, nullable=True)


class Wallet(Base):
    """Track influential wallets"""
    __tablename__ = "wallets"
    
    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, unique=True, index=True)
    
    # Statistics
    total_stakes = Column(Integer, default=0)
    total_staked_amount = Column(Float, default=0.0)
    avg_stake_size = Column(Float, default=0.0)
    avg_price_impact = Column(Float, default=0.0)
    
    # Tracking
    last_seen = Column(DateTime, default=datetime.utcnow)
    is_tracked = Column(Boolean, default=True)
    
    # Preferred subnets
    preferred_subnets = Column(String, nullable=True)  # JSON array of subnet IDs


class SubnetPool(Base):
    """Cache subnet pool states"""
    __tablename__ = "subnet_pools"
    
    id = Column(Integer, primary_key=True, index=True)
    subnet_id = Column(Integer, unique=True, index=True)
    
    # Pool state
    tao_reserve = Column(Float)
    alpha_reserve = Column(Float)
    current_price = Column(Float)
    
    # Metadata
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
