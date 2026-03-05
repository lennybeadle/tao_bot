"""
FastAPI server for frontend communication
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from bot.database import get_db, AsyncSessionLocal
from bot.models import Trade, Wallet, SubnetPool as SubnetPoolModel
from bot.config import config

app = FastAPI(title="TAO Staking Bot API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class TradeResponse(BaseModel):
    id: int
    timestamp: datetime
    subnet_id: int
    wallet_address: str
    wallet_stake: float
    bot_stake: float
    price_before: float
    price_after: Optional[float]
    expected_profit: float
    actual_profit: Optional[float]
    bot_stake_tx: Optional[str]
    bot_unstake_tx: Optional[str]
    wallet_tx: Optional[str]
    status: str
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class WalletResponse(BaseModel):
    id: int
    address: str
    total_stakes: int
    total_staked_amount: float
    avg_stake_size: float
    avg_price_impact: float
    last_seen: datetime
    is_tracked: bool
    
    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total_trades: int
    successful_trades: int
    total_profit: float
    avg_profit_per_trade: float
    trades_today: int
    profit_today: float


class ConfigResponse(BaseModel):
    min_wallet_stake: float
    max_bot_stake: float
    min_expected_profit: float
    bot_stake_ratio: float
    monitored_subnets: List[int]
    max_daily_trades: int
    max_slippage: float


@app.get("/")
async def root():
    return {"message": "TAO Staking Bot API"}


@app.get("/api/trades", response_model=List[TradeResponse])
async def get_trades(
    limit: int = 100,
    offset: int = 0,
    subnet_id: Optional[int] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get recent trades"""
    query = select(Trade)
    
    if subnet_id:
        query = query.where(Trade.subnet_id == subnet_id)
    if status:
        query = query.where(Trade.status == status)
    
    query = query.order_by(desc(Trade.timestamp)).limit(limit).offset(offset)
    
    result = await db.execute(query)
    trades = result.scalars().all()
    
    return trades


@app.get("/api/trades/{trade_id}", response_model=TradeResponse)
async def get_trade(trade_id: int, db: AsyncSession = Depends(get_db)):
    """Get specific trade"""
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()
    
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    return trade


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get bot statistics"""
    # Total trades
    total_result = await db.execute(select(func.count(Trade.id)))
    total_trades = total_result.scalar() or 0
    
    # Successful trades
    success_result = await db.execute(
        select(func.count(Trade.id)).where(Trade.status == "completed")
    )
    successful_trades = success_result.scalar() or 0
    
    # Total profit
    profit_result = await db.execute(
        select(func.sum(Trade.actual_profit)).where(Trade.actual_profit.isnot(None))
    )
    total_profit = profit_result.scalar() or 0.0
    
    # Average profit
    avg_profit = total_profit / successful_trades if successful_trades > 0 else 0.0
    
    # Today's stats
    today = datetime.utcnow().date()
    today_result = await db.execute(
        select(func.count(Trade.id)).where(
            func.date(Trade.timestamp) == today
        )
    )
    trades_today = today_result.scalar() or 0
    
    today_profit_result = await db.execute(
        select(func.sum(Trade.actual_profit)).where(
            func.date(Trade.timestamp) == today,
            Trade.actual_profit.isnot(None)
        )
    )
    profit_today = today_profit_result.scalar() or 0.0
    
    return StatsResponse(
        total_trades=total_trades,
        successful_trades=successful_trades,
        total_profit=total_profit,
        avg_profit_per_trade=avg_profit,
        trades_today=trades_today,
        profit_today=profit_today
    )


@app.get("/api/wallets", response_model=List[WalletResponse])
async def get_wallets(
    limit: int = 50,
    tracked_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Get tracked wallets"""
    query = select(Wallet)
    
    if tracked_only:
        query = query.where(Wallet.is_tracked == True)
    
    query = query.order_by(desc(Wallet.total_staked_amount)).limit(limit)
    
    result = await db.execute(query)
    wallets = result.scalars().all()
    
    return wallets


@app.get("/api/config", response_model=ConfigResponse)
async def get_config():
    """Get bot configuration"""
    return ConfigResponse(
        min_wallet_stake=config.min_wallet_stake,
        max_bot_stake=config.max_bot_stake,
        min_expected_profit=config.min_expected_profit,
        bot_stake_ratio=config.bot_stake_ratio,
        monitored_subnets=config.monitored_subnets,
        max_daily_trades=config.max_daily_trades,
        max_slippage=config.max_slippage
    )


@app.get("/api/pools")
async def get_pools(db: AsyncSession = Depends(get_db)):
    """Get subnet pool states"""
    result = await db.execute(select(SubnetPoolModel))
    pools = result.scalars().all()
    
    return [
        {
            "subnet_id": p.subnet_id,
            "tao_reserve": p.tao_reserve,
            "alpha_reserve": p.alpha_reserve,
            "current_price": p.current_price,
            "last_updated": p.last_updated.isoformat()
        }
        for p in pools
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.api_host, port=config.api_port)
