"""
Configuration management for TAO staking bot
"""
import os
import asyncio
from typing import List, Optional
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


def _get_default_monitored_subnets() -> List[int]:
    """Get default monitored subnets from environment variable"""
    return [int(x) for x in os.getenv("MONITORED_SUBNETS", "46,19,8").split(",")]


class BotConfig(BaseModel):
    """Bot configuration settings"""
    # RPC endpoints
    subtensor_rpc: str = os.getenv("SUBTENSOR_RPC", "wss://entrypoint-finney.opentensor.ai:443")
    
    # Wallet settings
    wallet_name: Optional[str] = os.getenv("WALLET_NAME")
    wallet_hotkey: Optional[str] = os.getenv("WALLET_HOTKEY")
    
    # Trading parameters
    min_wallet_stake: float = float(os.getenv("MIN_WALLET_STAKE", "30.0"))  # Minimum TAO to trigger
    max_bot_stake: float = float(os.getenv("MAX_BOT_STAKE", "100.0"))  # Maximum bot stake per trade
    min_expected_profit: float = float(os.getenv("MIN_EXPECTED_PROFIT", "0.05"))  # Minimum profit in TAO
    bot_stake_ratio: float = float(os.getenv("BOT_STAKE_RATIO", "0.5"))  # Bot stake as ratio of wallet stake
    min_wallet_reserve: float = float(os.getenv("MIN_WALLET_RESERVE", "0.02"))  # Minimum TAO to keep in wallet after staking
    
    # Subnets to monitor - loaded from database, cached
    _monitored_subnets_cache: Optional[List[int]] = None
    _monitored_subnets_cache_loaded: bool = False
    
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
    
    @property
    def monitored_subnets(self) -> List[int]:
        """Get monitored subnets from database cache, with fallback to env var"""
        # If not loaded yet, try to load from DB (synchronous fallback to env)
        if not self._monitored_subnets_cache_loaded:
            try:
                # Try to load from database synchronously
                loop = None
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                if loop.is_running():
                    # If loop is running, we can't use it synchronously
                    # Fall back to env var for now
                    self._monitored_subnets_cache = _get_default_monitored_subnets()
                else:
                    # Load from database
                    from bot.database import get_monitored_subnets
                    subnets = loop.run_until_complete(get_monitored_subnets())
                    if subnets:
                        self._monitored_subnets_cache = subnets
                    else:
                        # Fallback to env var
                        self._monitored_subnets_cache = _get_default_monitored_subnets()
            except Exception:
                # On any error, fall back to env var
                self._monitored_subnets_cache = _get_default_monitored_subnets()
            
            self._monitored_subnets_cache_loaded = True
        
        return self._monitored_subnets_cache or _get_default_monitored_subnets()
    
    async def reload_monitored_subnets(self):
        """Reload monitored subnets from database"""
        try:
            from bot.database import get_monitored_subnets
            subnets = await get_monitored_subnets()
            if subnets:
                self._monitored_subnets_cache = subnets
            else:
                self._monitored_subnets_cache = _get_default_monitored_subnets()
        except Exception:
            self._monitored_subnets_cache = _get_default_monitored_subnets()
        
        self._monitored_subnets_cache_loaded = True
    
    def invalidate_monitored_subnets_cache(self):
        """Invalidate the cache to force reload on next access"""
        self._monitored_subnets_cache_loaded = False
        self._monitored_subnets_cache = None


config = BotConfig()
