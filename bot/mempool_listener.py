"""
High-speed mempool listener optimized for detecting Bittensor subnet staking
"""

import asyncio
import logging
import time
from typing import Optional, Callable, Dict, Any, List

from substrateinterface import SubstrateInterface
from scalecodec import ScaleBytes
from bot.config import config

logger = logging.getLogger(__name__)


class MempoolListener:

    def __init__(self):

        self.substrates: List[SubstrateInterface] = []
        self.running = False
        self.callbacks: List[Callable] = []

        self.tx_cache: Dict[str, float] = {}

        self.rpc_endpoints = [
            config.subtensor_rpc,
            "wss://entrypoint-finney.opentensor.ai:443",
            "wss://archivelb-finney.opentensor.ai:443",
        ]

    async def connect(self):
        """Connect to multiple substrate nodes"""

        for rpc_url in self.rpc_endpoints:
            try:

                substrate = SubstrateInterface(
                    url=rpc_url,
                    ss58_format=42,
                    use_remote_preset=True
                )

                self.substrates.append(substrate)
                logger.info(f"Connected to {rpc_url}")

                if len(self.substrates) >= 2:
                    break

            except Exception as e:
                logger.warning(f"Failed connecting to {rpc_url}: {e}")

        if not self.substrates:
            raise Exception("No RPC nodes available")

    def register_callback(self, callback: Callable):
        self.callbacks.append(callback)

    async def _fetch_pending_extrinsics(self, substrate: SubstrateInterface):

        try:
            response = await asyncio.to_thread(
                substrate.rpc_request,
                "author_pendingExtrinsics",
                []
            )          
            pending = response.get("result", [])
            return pending

        except Exception as e:
            logger.debug(f"Pending fetch error: {e}")
            return []

    def _decode_extrinsic(self, substrate: SubstrateInterface, extrinsic_hex):

        try:
            extrinsic = substrate.decode_scale(
                "Extrinsic",
                ScaleBytes(extrinsic_hex)
            )

            call = extrinsic["call"]

            call_module = call["call_module"]
            call_function = call["call_function"]

            if call_module != "SubtensorModule":
                return None

            if call_function not in ("add_stake", "add_stake_limit"):
                return None

            args = {
                arg["name"]: arg["value"]
                for arg in call["call_args"]
            }

            netuid = int(args.get("netuid", -1))

            amount = args.get("amount_staked")

            if amount is None:
                return None

            amount = float(amount) / 1e9

            if amount < config.min_wallet_stake:
                return None
            logger.info(f"netuid: {netuid} amount: {amount}")
            return {
                "type": "stake",
                "netuid": netuid,
                "amount": amount,
                "hotkey_ss58": args.get("hotkey"),
                "timestamp": time.time()
            }

        except Exception as e:
            return None

    async def _safe_callback(self, callback, data):

        callback_name = callback.__name__ if hasattr(callback, '__name__') else str(callback)
        
        try:
            await callback(data)
        except Exception as e:
            logger.error(f"Callback failure ({callback_name}): {e}")

    async def _process_extrinsic(self, extrinsic_hex: str, idx: int, total: int, now: float):
        """Process a single extrinsic concurrently"""
        
        tx_hash = str(extrinsic_hex)
        
        # Cache check
        if tx_hash in self.tx_cache:
            if now - self.tx_cache[tx_hash] < 1:
                return

        # Decode extrinsic (run in thread pool since it's CPU-bound)
        decoded = None

        for substrate in self.substrates:
            # Run decode in thread pool to avoid blocking
            decoded = await asyncio.to_thread(
                self._decode_extrinsic,
                substrate,
                extrinsic_hex
            )
            if decoded:
                break

        if not decoded:
            return

        self.tx_cache[tx_hash] = now

        # Execute callbacks
        for callback in self.callbacks:
            asyncio.create_task(
                self._safe_callback(callback, decoded)
            )

    async def _process_mempool(self):

        tasks = [
            self._fetch_pending_extrinsics(sub)
            for sub in self.substrates
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        pending_extrinsics = []

        for r in results:
            if isinstance(r, list):
                pending_extrinsics.extend(r)

        now = time.time()

        # Process all extrinsics concurrently (fire and forget - no need to wait)
        for idx, extrinsic_hex in enumerate(pending_extrinsics):
            asyncio.create_task(
                self._process_extrinsic(extrinsic_hex, idx, len(pending_extrinsics), now)
            )

        

    async def start(self):

        await self.connect()

        self.running = True

        logger.info(
            f"Mempool listener started with {len(self.substrates)} nodes"
        )

        poll_interval = max(0.02, config.mempool_check_interval)

        while self.running:

            try:
                await self._process_mempool()

            except Exception as e:
                logger.error(f"Mempool loop error: {e}")

            sleep_time = poll_interval

            await asyncio.sleep(sleep_time)

    async def stop(self):

        self.running = False

        logger.info("Mempool listener stopped")