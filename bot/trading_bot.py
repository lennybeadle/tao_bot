"""
Main trading bot that orchestrates detection, simulation, and execution
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import bittensor as bt
from bot.config import config
from bot.mempool_listener import MempoolListener
from bot.price_simulator import PriceSimulator, SubnetPool
from bot.execution_engine import ExecutionEngine
from bot.database import AsyncSessionLocal
from bot.models import Trade, SubnetPool as SubnetPoolModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradingBot:
    """Main trading bot"""
    
    def __init__(self):
        self.mempool_listener = MempoolListener()
        self.execution_engine = ExecutionEngine()
        self.subtensor = bt.subtensor(network="finney")
        self.running = False
        self.daily_trades = 0
        self.last_reset = datetime.now().date()
        # In-memory pool cache for ultra-fast access
        self.pool_cache: Dict[int, tuple] = {}  # netuid -> (SubnetPool, timestamp)
        self.cache_ttl = 10  # Cache for 10 seconds
    
    async def initialize(self):
        """Initialize bot components"""
        logger.info("Initializing trading bot...")
        
        # Initialize execution engine
        await self.execution_engine.initialize()
        
        # Register mempool callback
        self.mempool_listener.register_callback(self._handle_stake_detection)
        
        # Initialize database
        from bot.database import init_db
        await init_db()
        
        logger.info("Trading bot initialized")
    
    async def _get_subnet_pool(self, netuid: int) -> Optional[SubnetPool]:
        """Get current subnet pool state - optimized with in-memory cache"""
        import time
        
        # Check in-memory cache first (fastest)
        if netuid in self.pool_cache:
            pool, cache_time = self.pool_cache[netuid]
            if time.time() - cache_time < self.cache_ttl:
                return pool
        
        # Cache miss - fetch fresh data (async, non-blocking)
        try:
            # Use thread pool for blocking subtensor calls
            loop = asyncio.get_event_loop()
            
            def _fetch_pool():
                try:
                    subnet_info = self.subtensor.subnet_info(netuid=netuid)
                    tao_reserve = float(subnet_info.get('tao_in', 1000))
                    alpha_reserve = float(subnet_info.get('alpha_in', 500))
                    return tao_reserve, alpha_reserve
                except Exception as e:
                    logger.warning(f"Could not fetch subnet info: {e}, using defaults")
                    # Fast fallback
                    return 1000.0, 500.0
            
            tao_reserve, alpha_reserve = await loop.run_in_executor(None, _fetch_pool)
            
            pool = SubnetPool(tao_reserve, alpha_reserve)
            
            # Update in-memory cache
            self.pool_cache[netuid] = (pool, time.time())
            
            # Update DB cache in background (non-blocking)
            asyncio.create_task(self._update_db_cache(netuid, tao_reserve, alpha_reserve))
            
            return pool
            
        except Exception as e:
            logger.error(f"Error getting subnet pool: {e}")
            return None
    
    async def _update_db_cache(self, netuid: int, tao_reserve: float, alpha_reserve: float):
        """Update database cache asynchronously"""
        try:
            async with AsyncSessionLocal() as session:
                pool_model = SubnetPoolModel(
                    subnet_id=netuid,
                    tao_reserve=tao_reserve,
                    alpha_reserve=alpha_reserve,
                    current_price=tao_reserve / alpha_reserve if alpha_reserve > 0 else 0
                )
                session.merge(pool_model)
                await session.commit()
        except Exception as e:
            logger.debug(f"Error updating DB cache: {e}")
    
    async def _handle_stake_detection(self, tx_data: Dict[str, Any]):
        """Handle detected stake transaction - optimized for speed"""
        import time
        start_time = time.time()
        
        if tx_data.get("type") != "stake":
            return
        
        # Reset daily counter if needed
        if datetime.now().date() > self.last_reset:
            self.daily_trades = 0
            self.last_reset = datetime.now().date()
        
        # Check daily limit
        if self.daily_trades >= config.max_daily_trades:
            return
        
        netuid = tx_data["netuid"]
        wallet_stake = tx_data["amount"]
        wallet_address = tx_data.get("hotkey_ss58", "unknown")
        
        logger.info(f"⚡ DETECTED: {wallet_stake} TAO stake on subnet {netuid}")
        
        # Parallel execution: get pool and simulate simultaneously
        pool_task = self._get_subnet_pool(netuid)
        
        # Get pool (cached, should be fast)
        pool = await pool_task
        if not pool:
            logger.warning(f"Could not get pool state for subnet {netuid}")
            return
        
        # Fast simulation (in-memory, no I/O)
        result = PriceSimulator.find_optimal_stake(
            pool=pool,
            wallet_stake=wallet_stake,
            max_bot_stake=config.max_bot_stake,
            min_profit=config.min_expected_profit
        )
        
        if not result:
            return
        
        optimal_stake, expected_profit, price_move = result
        
        decision_time = time.time() - start_time
        logger.info(
            f"✅ PROFITABLE! Bot: {optimal_stake} TAO, "
            f"Profit: {expected_profit:.4f} TAO, "
            f"Move: {price_move:.2f}%, "
            f"Decision: {decision_time*1000:.1f}ms"
        )
        
        # Create trade data
        trade_id = f"{netuid}_{wallet_address}_{time.time()}"
        
        trade_data = {
            "subnet_id": netuid,
            "wallet_address": wallet_address,
            "wallet_stake": wallet_stake,
            "bot_stake": optimal_stake,
            "price_before": pool.price(),
            "expected_profit": expected_profit,
            "status": "pending",
            "wallet_tx": tx_data.get("tx_hash")
        }
        
        # Execute trade immediately (don't await - fire and continue)
        asyncio.create_task(self._execute_trade(trade_id, trade_data, pool))
    
    async def _execute_trade(
        self,
        trade_id: str,
        trade_data: Dict[str, Any],
        pool: SubnetPool
    ):
        """Execute front-run trade"""
        try:
            netuid = trade_data["subnet_id"]
            bot_stake = trade_data["bot_stake"]
            
            # Step 1: Bot stakes
            logger.info(f"Executing bot stake: {bot_stake} TAO on subnet {netuid}")
            stake_tx = await self.execution_engine.execute_stake(
                netuid=netuid,
                amount=bot_stake,
                trade_id=trade_id
            )
            
            if not stake_tx:
                logger.error("Bot stake failed")
                trade_data["status"] = "failed"
                trade_data["error_message"] = "Bot stake transaction failed"
                await self._record_trade(trade_data)
                return
            
            trade_data["bot_stake_tx"] = stake_tx
            trade_data["status"] = "staked"
            
            # Wait for wallet stake to execute (monitor block)
            logger.info("Waiting for wallet stake to execute...")
            await asyncio.sleep(12)  # Approximate block time
            
            # Step 2: Bot unstakes
            logger.info(f"Executing bot unstake: {bot_stake} TAO from subnet {netuid}")
            unstake_tx = await self.execution_engine.execute_unstake(
                netuid=netuid,
                amount=bot_stake,
                trade_id=trade_id
            )
            
            if not unstake_tx:
                logger.error("Bot unstake failed")
                trade_data["status"] = "failed"
                trade_data["error_message"] = "Bot unstake transaction failed"
            else:
                trade_data["bot_unstake_tx"] = unstake_tx
                trade_data["status"] = "completed"
                
                # Calculate actual profit (simplified)
                # In production, you'd query the actual balance change
                trade_data["actual_profit"] = trade_data["expected_profit"]
            
            # Record trade asynchronously (non-blocking)
            await self.execution_engine.record_trade_async(trade_data)
            self.daily_trades += 1
            
            logger.info(f"✅ Trade completed: {trade_id}")
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            trade_data["status"] = "failed"
            trade_data["error_message"] = str(e)
            await self._record_trade(trade_data)
    
    async def _record_trade(self, trade_data: Dict[str, Any]):
        """Record trade in database"""
        try:
            async with AsyncSessionLocal() as session:
                trade = Trade(**trade_data)
                session.add(trade)
                await session.commit()
        except Exception as e:
            logger.error(f"Error recording trade: {e}")
    
    async def start(self):
        """Start the trading bot"""
        self.running = True
        logger.info("Starting trading bot...")
        
        # Start mempool listener
        await self.mempool_listener.start()
    
    async def stop(self):
        """Stop the trading bot"""
        self.running = False
        await self.mempool_listener.stop()
        logger.info("Trading bot stopped")


async def main():
    """Main entry point"""
    bot = TradingBot()
    await bot.initialize()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
