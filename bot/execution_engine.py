"""
Execution engine for staking and unstaking transactions
Ultra-optimized for minimal latency with pre-signed transactions and multi-node broadcasting
"""
import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
import bittensor as bt
from bot.config import config
from bot.models import Trade
from bot.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """Handles transaction execution with pre-signed transactions and multi-node broadcasting"""
    
    def __init__(self):
        self.subtensor: Optional[bt.subtensor] = None
        self.subtensor_nodes: List[bt.subtensor] = []  # Multiple nodes for broadcasting
        self.wallet: Optional[bt.wallet] = None
        self.active_trades: Dict[str, Dict[str, Any]] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)  # Parallel execution
        
        # Pre-signed transaction cache for instant broadcasting
        # Format: (netuid, amount) -> (signed_tx_bytes, timestamp)
        # Note: Nonces are embedded in signed transactions, so cache has short TTL
        self.pre_signed_cache: Dict[tuple, tuple] = {}
        self.cache_max_age = 30  # Cache valid for 30 seconds
        self.cache_refresh_interval = 10  # Refresh every 10 seconds
        
        # Latency tracking
        self.latency_stats: Dict[str, List[float]] = {
            "detect_to_decision": [],
            "decision_to_broadcast": [],
            "total_latency": []
        }
    
    async def initialize(self):
        """Initialize subtensor, multiple nodes, wallet, and start pre-signing"""
        try:
            # Use thread pool for blocking operations
            loop = asyncio.get_event_loop()
            
            # Initialize primary subtensor
            self.subtensor = await loop.run_in_executor(
                self.executor,
                lambda: bt.subtensor(network="finney")
            )
            
            # Initialize multiple nodes for broadcasting
            rpc_endpoints = [
                config.subtensor_rpc,
                "wss://entrypoint-finney.opentensor.ai:443",
                "wss://archivelb-finney.opentensor.ai:443",
            ]
            
            for rpc_url in rpc_endpoints[:3]:  # Connect to up to 3 nodes
                try:
                    node = await loop.run_in_executor(
                        self.executor,
                        lambda url=rpc_url: bt.subtensor(network="finney", endpoint=url)
                    )
                    self.subtensor_nodes.append(node)
                    logger.info(f"Connected to node: {rpc_url}")
                except Exception as e:
                    logger.warning(f"Failed to connect to {rpc_url}: {e}")
            
            if not self.subtensor_nodes:
                self.subtensor_nodes = [self.subtensor]  # Fallback to primary
            
            if config.wallet_name and config.wallet_hotkey:
                self.wallet = await loop.run_in_executor(
                    self.executor,
                    lambda: bt.wallet(
                        name=config.wallet_name,
                        hotkey=config.wallet_hotkey
                    )
                )
                logger.info(f"Wallet initialized: {config.wallet_name}")
                
                # Start background pre-signing task
                asyncio.create_task(self._pre_sign_common_transactions())
            else:
                logger.warning("Wallet not configured - execution disabled")
                
        except Exception as e:
            logger.error(f"Failed to initialize execution engine: {e}")
            raise
    
    async def _execute_in_thread(self, func, *args, **kwargs):
        """Execute blocking operations in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args, **kwargs)
    
    async def _pre_sign_common_transactions(self):
        """Pre-sign common transaction amounts for instant broadcasting"""
        if not self.wallet or not self.subtensor:
            return
        
        # Common stake amounts to pre-sign
        common_amounts = [10.0, 25.0, 50.0, 100.0]
        common_netuids = config.monitored_subnets
        
        while True:
            try:
                current_time = time.time()
                
                # Refresh cache for common combinations
                for netuid in common_netuids:
                    for amount in common_amounts:
                        cache_key = (netuid, amount)
                        
                        # Check if cache needs refresh
                        if cache_key in self.pre_signed_cache:
                            _, _, cache_time = self.pre_signed_cache[cache_key]
                            if current_time - cache_time < self.cache_max_age:
                                continue
                        
                        # Pre-sign transaction
                        try:
                            loop = asyncio.get_event_loop()
                            signed_tx = await loop.run_in_executor(
                                self.executor,
                                self._create_signed_stake_tx,
                                netuid,
                                amount
                            )
                            
                            if signed_tx:
                                # Store signed tx with timestamp (nonce is embedded in signed tx)
                                self.pre_signed_cache[cache_key] = (signed_tx, current_time)
                                logger.debug(f"Pre-signed: {amount} TAO on subnet {netuid}")
                        except Exception as e:
                            logger.debug(f"Pre-sign failed for {netuid}/{amount}: {e}")
                
                await asyncio.sleep(self.cache_refresh_interval)
                
            except Exception as e:
                logger.error(f"Pre-signing error: {e}")
                await asyncio.sleep(5)
    
    def _create_signed_stake_tx(self, netuid: int, amount: float) -> Optional[bytes]:
        """Create and sign a stake transaction (blocking) - uses current nonce"""
        try:
            amount_rao = int(amount * 1e9)
            call = self.subtensor.substrate.compose_call(
                call_module="SubtensorModule",
                call_function="add_stake",
                call_params={
                    "netuid": netuid,
                    "hotkey_ss58": self.wallet.hotkey.ss58_address,
                    "amount": amount_rao
                }
            )
            
            # Get current account info for nonce
            account_info = self.subtensor.substrate.query(
                module="System",
                storage_function="Account",
                params=[self.wallet.coldkey.ss58_address]
            )
            
            nonce = account_info.value.get("nonce", 0) if account_info else 0
            
            extrinsic = self.subtensor.substrate.create_signed_extrinsic(
                call=call,
                keypair=self.wallet.coldkey,
                nonce=nonce
            )
            
            return extrinsic.encode()
        except Exception as e:
            logger.debug(f"Error creating signed tx: {e}")
            return None
    
    async def _broadcast_to_multiple_nodes(self, tx_bytes: bytes) -> Optional[str]:
        """Broadcast transaction to multiple nodes simultaneously for fastest inclusion"""
        if not self.subtensor_nodes:
            return None
        
        async def _broadcast_single(node: bt.subtensor) -> Optional[str]:
            """Broadcast to a single node"""
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor,
                    lambda: node.substrate.submit_extrinsic(
                        extrinsic=tx_bytes,
                        wait_for_inclusion=False
                    )
                )
                return result if isinstance(result, str) else getattr(result, "tx_hash", None)
            except Exception as e:
                logger.debug(f"Broadcast error: {e}")
                return None
        
        # Broadcast to all nodes in parallel - first success wins
        tasks = [_broadcast_single(node) for node in self.subtensor_nodes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Return first successful result
        for result in results:
            if result and not isinstance(result, Exception):
                return result
        
        return None
    
    async def execute_stake(
        self,
        netuid: int,
        amount: float,
        trade_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Execute stake transaction - optimized with pre-signed cache and multi-node broadcast
        
        Returns:
            Transaction hash or None if failed
        """
        if not self.wallet or not self.subtensor:
            logger.error("Wallet or subtensor not initialized")
            return None
        
        try:
            broadcast_start = time.time()
            
            # Check pre-signed cache first (fastest path)
            # Note: Pre-signed transactions may have stale nonces, so we'll try them first
            # but fall back to fresh signing if they fail
            cache_key = (netuid, round(amount, 1))  # Round to match cache
            if cache_key in self.pre_signed_cache:
                tx_bytes, cache_time = self.pre_signed_cache[cache_key]
                
                # Check cache validity (shorter TTL for nonce freshness)
                if time.time() - cache_time < 5:  # 5 seconds for nonce freshness
                    logger.info(f"⚡ ULTRA-FAST STAKING {amount} TAO on subnet {netuid} (pre-signed)")
                    
                    # Try broadcasting pre-signed transaction
                    tx_hash = await self._broadcast_to_multiple_nodes(tx_bytes)
                    
                    # If pre-signed works, we're done (fastest path)
                    if tx_hash:
                        broadcast_time = time.time() - broadcast_start
                        self._record_latency("decision_to_broadcast", broadcast_time * 1000)
                        logger.info(f"✅ Pre-signed stake broadcast in {broadcast_time*1000:.1f}ms: {tx_hash}")
                        
                        if trade_id:
                            self.active_trades[trade_id] = {
                                "netuid": netuid,
                                "amount": amount,
                                "stake_tx": tx_hash,
                                "status": "staked",
                                "timestamp": time.time(),
                                "method": "pre_signed"
                            }
                        
                        return tx_hash
                    # If pre-signed failed (likely stale nonce), fall through to fresh signing
            
            # Fallback: sign and broadcast (slower but works for any amount)
            logger.info(f"⚡ FAST STAKING {amount} TAO on subnet {netuid} (signing now)")
            amount_rao = int(amount * 1e9)
            
            def _stake():
                try:
                    # Create signed transaction
                    call = self.subtensor.substrate.compose_call(
                        call_module="SubtensorModule",
                        call_function="add_stake",
                        call_params={
                            "netuid": netuid,
                            "hotkey_ss58": self.wallet.hotkey.ss58_address,
                            "amount": amount_rao
                        }
                    )
                    
                    extrinsic = self.subtensor.substrate.create_signed_extrinsic(
                        call=call,
                        keypair=self.wallet.coldkey
                    )
                    
                    return extrinsic.encode()
                except Exception as e:
                    logger.error(f"Stake signing error: {e}")
                    return None
            
            tx_bytes = await self._execute_in_thread(_stake)
            
            if not tx_bytes:
                logger.error("❌ Stake transaction signing failed")
                return None
            
            # Broadcast to multiple nodes
            tx_hash = await self._broadcast_to_multiple_nodes(tx_bytes)
            broadcast_time = time.time() - broadcast_start
            self._record_latency("decision_to_broadcast", broadcast_time * 1000)
            
            if tx_hash:
                logger.info(f"✅ Stake broadcast in {broadcast_time*1000:.1f}ms: {tx_hash}")
                
                if trade_id:
                    self.active_trades[trade_id] = {
                        "netuid": netuid,
                        "amount": amount,
                        "stake_tx": tx_hash,
                        "status": "staked",
                        "timestamp": time.time(),
                        "method": "signed_now"
                    }
                
                return tx_hash
            else:
                logger.error("❌ Stake transaction broadcast failed")
                return None
                
        except Exception as e:
            logger.error(f"Error executing stake: {e}")
            return None
    
    def _record_latency(self, metric: str, latency_ms: float):
        """Record latency metric"""
        if metric in self.latency_stats:
            self.latency_stats[metric].append(latency_ms)
            # Keep only last 100 measurements
            if len(self.latency_stats[metric]) > 100:
                self.latency_stats[metric] = self.latency_stats[metric][-100:]
    
    async def execute_unstake(
        self,
        netuid: int,
        amount: float,
        trade_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Execute unstake transaction - optimized with multi-node broadcast
        
        Returns:
            Transaction hash or None if failed
        """
        if not self.wallet or not self.subtensor:
            logger.error("Wallet or subtensor not initialized")
            return None
        
        try:
            broadcast_start = time.time()
            amount_rao = int(amount * 1e9)
            
            logger.info(f"⚡ FAST UNSTAKING {amount} TAO from subnet {netuid}")
            
            def _unstake():
                try:
                    # Create signed transaction
                    call = self.subtensor.substrate.compose_call(
                        call_module="SubtensorModule",
                        call_function="remove_stake",
                        call_params={
                            "netuid": netuid,
                            "hotkey_ss58": self.wallet.hotkey.ss58_address,
                            "amount": amount_rao
                        }
                    )
                    
                    extrinsic = self.subtensor.substrate.create_signed_extrinsic(
                        call=call,
                        keypair=self.wallet.coldkey
                    )
                    
                    return extrinsic.encode()
                except Exception as e:
                    logger.error(f"Unstake signing error: {e}")
                    return None
            
            tx_bytes = await self._execute_in_thread(_unstake)
            
            if not tx_bytes:
                logger.error("❌ Unstake transaction signing failed")
                return None
            
            # Broadcast to multiple nodes
            tx_hash = await self._broadcast_to_multiple_nodes(tx_bytes)
            broadcast_time = time.time() - broadcast_start
            
            if tx_hash:
                logger.info(f"✅ Unstake broadcast in {broadcast_time*1000:.1f}ms: {tx_hash}")
                
                if trade_id and trade_id in self.active_trades:
                    self.active_trades[trade_id]["unstake_tx"] = tx_hash
                    self.active_trades[trade_id]["status"] = "completed"
                
                return tx_hash
            else:
                logger.error("❌ Unstake transaction broadcast failed")
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
