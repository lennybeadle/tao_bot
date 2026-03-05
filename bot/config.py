"""
Configuration management for TAO staking bot
"""
import os
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class BotConfig(BaseModel):
    """Bot configuration settings"""
    # RPC endpoints
    subtensor_rpc: str = os.getenv("SUBTENSOR_RPC", "wss://entrypoint-finney.opentensor.ai:443")
    
    # Wallet settings
    wallet_name: Optional[str] = os.getenv("WALLET_NAME")
    wallet_hotkey: Optional[str] = os.getenv("WALLET_HOTKEY")
    
    # Trading parameters
    min_wallet_stake: float = float(os.getenv("MIN_WALLET_STAKE", "10.0"))  # Minimum TAO to trigger
    max_bot_stake: float = float(os.getenv("MAX_BOT_STAKE", "100.0"))  # Maximum bot stake per trade
    min_expected_profit: float = float(os.getenv("MIN_EXPECTED_PROFIT", "0.05"))  # Minimum profit in TAO
    bot_stake_ratio: float = float(os.getenv("BOT_STAKE_RATIO", "0.5"))  # Bot stake as ratio of wallet stake
    
    # Subnets to monitor
    monitored_subnets: List[int] = [int(x) for x in os.getenv("MONITORED_SUBNETS", "46,19,8").split(",")]
    
    # Risk management
    max_daily_trades: int = int(os.getenv("MAX_DAILY_TRADES", "50"))
    max_slippage: float = float(os.getenv("MAX_SLIPPAGE", "0.05"))  # 5% max slippage
    
    # Performance (optimized for speed)
    mempool_check_interval: float = float(os.getenv("MEMPOOL_CHECK_INTERVAL", "0.05"))  # 50ms - ultra-fast
    transaction_timeout: float = float(os.getenv("TRANSACTION_TIMEOUT", "30.0"))  # seconds
    use_multiple_rpc: bool = os.getenv("USE_MULTIPLE_RPC", "true").lower() == "true"
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")
    
    # API
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))


config = BotConfig()
