"""
Execution engine for staking and unstaking transactions
"""
import asyncio
import logging
from typing import Optional, Dict, Any
import bittensor as bt
from bot.config import config
from bot.models import Trade
from bot.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """Handles transaction execution"""
    
    def __init__(self):
        self.subtensor: Optional[bt.subtensor] = None
        self.wallet: Optional[bt.wallet] = None
        self.active_trades: Dict[str, Dict[str, Any]] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)  # Parallel execution
    
    async def initialize(self):
        """Initialize subtensor and wallet"""
        try:
            # Use thread pool for blocking operations
            loop = asyncio.get_event_loop()
            self.subtensor = await loop.run_in_executor(
                self.executor,
                lambda: bt.subtensor(network="finney")
            )
            
            if config.wallet_name and config.wallet_hotkey:
                self.wallet = await loop.run_in_executor(
                    self.executor,
                    lambda: bt.wallet(
                        name=config.wallet_name,
                        hotkey=config.wallet_hotkey
                    )
                )
                logger.info(f"Wallet initialized: {config.wallet_name}")
            else:
                logger.warning("Wallet not configured - execution disabled")
                
        except Exception as e:
            logger.error(f"Failed to initialize execution engine: {e}")
            raise
    
    async def _execute_in_thread(self, func, *args, **kwargs):
        """Execute blocking operations in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args, **kwargs)
    
    async def execute_stake(
        self,
        netuid: int,
        amount: float,
        trade_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Execute stake transaction
        
        Returns:
            Transaction hash or None if failed
        """
        if not self.wallet or not self.subtensor:
            logger.error("Wallet or subtensor not initialized")
            return None
        
        try:
            amount_rao = int(amount * 1e9)
            
            logger.info(f"⚡ FAST STAKING {amount} TAO on subnet {netuid}")
            start_time = time.time()
            
            # Execute in thread pool to avoid blocking
            def _stake():
                try:
                    result = self.subtensor.add_stake(
                        wallet=self.wallet,
                        netuid=netuid,
                        amount=amount_rao,
                        wait_for_inclusion=False,  # Don't wait, fire and forget
                        prompt=False
                    )
                    return result
                except Exception as e:
                    logger.error(f"Stake execution error: {e}")
                    return None
            
            result = await self._execute_in_thread(_stake)
            elapsed = time.time() - start_time
            
            if result:
                tx_hash = result if isinstance(result, str) else getattr(result, "tx_hash", None)
                logger.info(f"✅ Stake successful in {elapsed*1000:.1f}ms: {tx_hash}")
                
                if trade_id:
                    self.active_trades[trade_id] = {
                        "netuid": netuid,
                        "amount": amount,
                        "stake_tx": tx_hash,
                        "status": "staked",
                        "timestamp": time.time()
                    }
                
                return tx_hash
            else:
                logger.error("❌ Stake transaction failed")
                return None
                
        except Exception as e:
            logger.error(f"Error executing stake: {e}")
            return None
    
    async def execute_unstake(
        self,
        netuid: int,
        amount: float,
        trade_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Execute unstake transaction
        
        Returns:
            Transaction hash or None if failed
        """
        if not self.wallet or not self.subtensor:
            logger.error("Wallet or subtensor not initialized")
            return None
        
        try:
            amount_rao = int(amount * 1e9)
            
            logger.info(f"⚡ FAST UNSTAKING {amount} TAO from subnet {netuid}")
            start_time = time.time()
            
            def _unstake():
                try:
                    result = self.subtensor.unstake(
                        wallet=self.wallet,
                        netuid=netuid,
                        amount=amount_rao,
                        wait_for_inclusion=False,  # Don't wait
                        prompt=False
                    )
                    return result
                except Exception as e:
                    logger.error(f"Unstake execution error: {e}")
                    return None
            
            result = await self._execute_in_thread(_unstake)
            elapsed = time.time() - start_time
            
            if result:
                tx_hash = result if isinstance(result, str) else getattr(result, "tx_hash", None)
                logger.info(f"✅ Unstake successful in {elapsed*1000:.1f}ms: {tx_hash}")
                
                if trade_id and trade_id in self.active_trades:
                    self.active_trades[trade_id]["unstake_tx"] = tx_hash
                    self.active_trades[trade_id]["status"] = "completed"
                
                return tx_hash
            else:
                logger.error("❌ Unstake transaction failed")
                return None
                
        except Exception as e:
            logger.error(f"Error executing unstake: {e}")
            return None
    
    async def record_trade_async(self, trade_data: Dict[str, Any]):
        """Record trade in database asynchronously (non-blocking)"""
        # Fire and forget - don't wait for DB write
        asyncio.create_task(self._record_trade(trade_data))
    
    async def _record_trade(self, trade_data: Dict[str, Any]):
        """Record trade in database"""
        try:
            async with AsyncSessionLocal() as session:
                trade = Trade(**trade_data)
                session.add(trade)
                await session.commit()
        except Exception as e:
            logger.error(f"Error recording trade: {e}")
