"""
High-speed mempool listener with WebSocket subscriptions and multiple RPC endpoints
"""
import asyncio
import logging
import time
from typing import Optional, Callable, Dict, Any, List
from substrateinterface import SubstrateInterface
from bot.config import config

logger = logging.getLogger(__name__)


class MempoolListener:
    """Ultra-fast mempool listener with multiple RPC endpoints"""
    
    def __init__(self):
        self.substrates: List[SubstrateInterface] = []
        self.running = False
        self.callbacks: list[Callable] = []
        self.last_seen_txs: set = set()
        self.tx_cache: Dict[str, float] = {}  # tx_hash -> timestamp
        self.pool_state_cache: Dict[int, tuple] = {}  # netuid -> (tao, alpha, timestamp)
        
        # Multiple RPC endpoints for redundancy and speed
        self.rpc_endpoints = [
            config.subtensor_rpc,
            "wss://entrypoint-finney.opentensor.ai:443",
            "wss://archivelb-finney.opentensor.ai:443",
        ]
    
    async def connect(self):
        """Connect to multiple Substrate nodes for redundancy"""
        for rpc_url in self.rpc_endpoints:
            try:
                substrate = SubstrateInterface(
                    url=rpc_url,
                    ss58_format=42,
                    use_remote_preset=True
                )
                self.substrates.append(substrate)
                logger.info(f"Connected to {rpc_url}")
                if len(self.substrates) >= 2:  # At least 2 connections
                    break
            except Exception as e:
                logger.warning(f"Failed to connect to {rpc_url}: {e}")
                continue
        
        if not self.substrates:
            raise Exception("Failed to connect to any RPC endpoint")
    
    def register_callback(self, callback: Callable):
        """Register callback for stake detection"""
        self.callbacks.append(callback)
    
    async def _process_pending_extrinsics(self):
        """Process pending extrinsics from mempool - optimized for speed"""
        if not self.substrates:
            return
        
        # Process from all connected substrates in parallel
        tasks = [self._fetch_from_substrate(sub) for sub in self.substrates]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Merge results, prioritizing first non-empty result
        all_txs = {}
        for result in results:
            if isinstance(result, dict):
                all_txs.update(result)
        
        # Process new transactions
        current_time = time.time()
        for tx_hash, tx_data in all_txs.items():
            # Skip if already processed recently (within 1 second)
            if tx_hash in self.tx_cache:
                if current_time - self.tx_cache[tx_hash] < 1.0:
                    continue
            
            decoded = self._decode_transaction_fast(tx_data)
            
            if decoded:
                self.tx_cache[tx_hash] = current_time
                self.last_seen_txs.add(tx_hash)
                
                # Fire callbacks in parallel (don't await)
                for callback in self.callbacks:
                    asyncio.create_task(self._safe_callback(callback, decoded))
        
        # Clean old cache entries (older than 60 seconds)
        cutoff = current_time - 60
        self.tx_cache = {k: v for k, v in self.tx_cache.items() if v > cutoff}
        
        # Clean old hashes
        if len(self.last_seen_txs) > 2000:
            self.last_seen_txs = set(list(self.last_seen_txs)[-1000:])
    
    async def _fetch_from_substrate(self, substrate: SubstrateInterface) -> Dict[str, Any]:
        """Fetch pending extrinsics from a substrate node"""
        try:
            pending = substrate.rpc_request("author_pendingExtrinsics", [])
            return {tx.get("hash", ""): tx for tx in pending if tx.get("hash")}
        except Exception as e:
            logger.debug(f"Error fetching from substrate: {e}")
            return {}
    
    async def _safe_callback(self, callback: Callable, data: Dict[str, Any]):
        """Safely execute callback"""
        try:
            await callback(data)
        except Exception as e:
            logger.error(f"Callback error: {e}")
    
    def _decode_transaction_fast(self, tx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Ultra-fast transaction decoding - optimized for speed"""
        try:
            call = tx.get("call", {})
            call_module = call.get("call_module")
            call_function = call.get("call_function")
            
            # Fast path: check module/function first before parsing args
            if call_module != "SubtensorModule":
                return None
            
            if call_function not in ("add_stake", "remove_stake"):
                return None
            
            # Fast arg extraction using dict comprehension
            call_args = call.get("call_args", [])
            args_dict = {arg.get("name"): arg.get("value") for arg in call_args}
            
            netuid = args_dict.get("netuid")
            if netuid is None:
                return None
            
            netuid = int(netuid)
            
            # Quick subnet filter (set lookup is O(1))
            if netuid not in config.monitored_subnets:
                return None
            
            if call_function == "add_stake":
                amount = args_dict.get("amount")
                if amount is None:
                    return None
                
                amount = float(amount) / 1e9  # RAO to TAO
                
                # Fast threshold check
                if amount < config.min_wallet_stake:
                    return None
                
                return {
                    "type": "stake",
                    "netuid": netuid,
                    "amount": amount,
                    "hotkey_ss58": args_dict.get("hotkey_ss58", ""),
                    "tx_hash": tx.get("hash", ""),
                    "timestamp": time.time()
                }
            
            elif call_function == "remove_stake":
                amount = args_dict.get("amount")
                return {
                    "type": "unstake",
                    "netuid": netuid,
                    "amount": float(amount) / 1e9 if amount else None,
                    "hotkey_ss58": args_dict.get("hotkey_ss58", ""),
                    "tx_hash": tx.get("hash", ""),
                    "timestamp": time.time()
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Error decoding transaction: {e}")
            return None
    
    async def start(self):
        """Start listening to mempool with high-frequency polling"""
        self.running = True
        await self.connect()
        
        logger.info(f"Mempool listener started with {len(self.substrates)} RPC connections")
        
        # Use very short interval for maximum speed
        check_interval = max(0.05, config.mempool_check_interval)  # Minimum 50ms
        
        while self.running:
            try:
                start_time = time.time()
                await self._process_pending_extrinsics()
                elapsed = time.time() - start_time
                
                # Adaptive sleep: if processing is fast, sleep less
                sleep_time = max(0.01, check_interval - elapsed)
                await asyncio.sleep(sleep_time)
            except Exception as e:
                logger.error(f"Mempool listener error: {e}")
                await asyncio.sleep(0.1)
    
    async def stop(self):
        """Stop listening"""
        self.running = False
        logger.info("Mempool listener stopped")
