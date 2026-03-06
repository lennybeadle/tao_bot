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
    """Main trading bot - optimized for minimal latency"""
    
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
        
        # Latency tracking
        self.latency_metrics = {
            "detect_to_decision": [],
            "decision_to_execute": [],
            "total_pipeline": []
        }
    
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
        
        # Start background liquidity updater
        asyncio.create_task(self._background_liquidity_updater())
        
        logger.info("Trading bot initialized")
    
    async def _background_liquidity_updater(self):
        """Background task to update liquidity cache every block (~12 seconds)"""
        last_block = 0
        
        while self.running:
            try:
                # Get current block
                loop = asyncio.get_event_loop()
                current_block = await loop.run_in_executor(
                    None,
                    lambda: self.subtensor.get_current_block()
                )
                
                # Update cache if new block
                if current_block > last_block:
                    last_block = current_block
                    
                    # Update liquidity for all monitored subnets in parallel
                    tasks = [
                        self._get_subnet_pool(netuid) 
                        for netuid in config.monitored_subnets
                    ]
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
                    logger.debug(f"Liquidity cache updated at block {current_block}")
                
                # Check every 2 seconds (faster than block time for responsiveness)
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.debug(f"Liquidity updater error: {e}")
                await asyncio.sleep(5)
    
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
        """Handle detected stake transaction - optimized for speed with latency tracking"""
        import time
        pipeline_start = time.time()
        detect_time = tx_data.get("timestamp", pipeline_start)
        
        if tx_data.get("type") != "stake":
            return
        
        # Reset daily counter if needed
        if datetime.now().date() > self.last_reset:
            self.daily_trades = 0
            self.last_reset = datetime.now().date()
        
        # Check daily limit (fast check, no I/O)
        if self.daily_trades >= config.max_daily_trades:
            return
        
        netuid = tx_data["netuid"]
        wallet_stake = tx_data["amount"]
        wallet_address = tx_data.get("hotkey_ss58", "unknown")
        
        # Ultra-fast filter: quick threshold check before any computation
        if wallet_stake < config.min_wallet_stake:
            return
        
        logger.info(f"⚡ DETECTED: {wallet_stake} TAO stake on subnet {netuid}")
        
        decision_start = time.time()
        
        # Get pool (cached, should be <1ms)
        pool = await self._get_subnet_pool(netuid)
        if not pool:
            logger.warning(f"Could not get pool state for subnet {netuid}")
            return
        
        # Fast simulation (in-memory, no I/O) - target <5ms
        result = PriceSimulator.find_optimal_stake(
            pool=pool,
            wallet_stake=wallet_stake,
            max_bot_stake=config.max_bot_stake,
            min_profit=config.min_expected_profit
        )
        
        decision_time = time.time() - decision_start
        self._record_latency("detect_to_decision", decision_time * 1000)
        
        if not result:
            return
        
        optimal_stake, expected_profit, price_move = result
        
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
            "wallet_tx": tx_data.get("tx_hash"),
            "detect_timestamp": detect_time,
            "decision_timestamp": decision_start
        }
        
        # Execute trade immediately (don't await - fire and continue)
        execute_start = time.time()
        asyncio.create_task(self._execute_trade(trade_id, trade_data, pool, execute_start))
        
        # Record total pipeline latency
        total_time = time.time() - pipeline_start
        self._record_latency("total_pipeline", total_time * 1000)
    
    def _record_latency(self, metric: str, latency_ms: float):
        """Record latency metric"""
        if metric in self.latency_metrics:
            self.latency_metrics[metric].append(latency_ms)
            # Keep only last 100 measurements
            if len(self.latency_metrics[metric]) > 100:
                self.latency_metrics[metric] = self.latency_metrics[metric][-100:]
            
            # Log statistics periodically
            if len(self.latency_metrics[metric]) % 10 == 0:
                metrics = self.latency_metrics[metric]
                avg = sum(metrics) / len(metrics)
                min_lat = min(metrics)
                max_lat = max(metrics)
                logger.info(
                    f"📊 {metric}: avg={avg:.1f}ms, min={min_lat:.1f}ms, max={max_lat:.1f}ms"
                )
    
    async def _execute_trade(
        self,
        trade_id: str,
        trade_data: Dict[str, Any],
        pool: SubnetPool,
        execute_start: float
    ):
        """Execute front-run trade with latency tracking"""
        import time
        try:
            netuid = trade_data["subnet_id"]
            bot_stake = trade_data["bot_stake"]
            
            # Step 1: Bot stakes
            logger.info(f"Executing bot stake: {bot_stake} TAO on subnet {netuid}")
            stake_start = time.time()
            stake_tx = await self.execution_engine.execute_stake(
                netuid=netuid,
                amount=bot_stake,
                trade_id=trade_id
            )
            
            execute_time = time.time() - execute_start
            self._record_latency("decision_to_execute", execute_time * 1000)
            
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
    
    def get_latency_stats(self) -> Dict[str, Dict[str, float]]:
        """Get latency statistics"""
        stats = {}
        for metric, values in self.latency_metrics.items():
            if values:
                stats[metric] = {
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "p50": sorted(values)[len(values) // 2],
                    "p95": sorted(values)[int(len(values) * 0.95)] if len(values) > 1 else values[0],
                    "count": len(values)
                }
        return stats
    
    async def stop(self):
        """Stop the trading bot"""
        self.running = False
        await self.mempool_listener.stop()
        
        # Print final latency statistics
        stats = self.get_latency_stats()
        if stats:
            logger.info("📊 Final Latency Statistics:")
            for metric, stat in stats.items():
                logger.info(
                    f"  {metric}: avg={stat['avg']:.1f}ms, "
                    f"min={stat['min']:.1f}ms, max={stat['max']:.1f}ms, "
                    f"p95={stat['p95']:.1f}ms"
                )
        
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
