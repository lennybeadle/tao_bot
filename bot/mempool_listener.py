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
            fetch_start = time.time()
            response = await asyncio.to_thread(
                substrate.rpc_request,
                "author_pendingExtrinsics",
                []
            )          
            fetch_time = (time.time() - fetch_start) * 1000
            pending = response.get("result", [])
            logger.debug(f"⏱️ _fetch_pending_extrinsics: {fetch_time:.2f}ms, found {len(pending)} extrinsics")
            return pending

        except Exception as e:
            logger.debug(f"Pending fetch error: {e}")
            return []

    def _decode_extrinsic(self, substrate: SubstrateInterface, extrinsic_hex):

        decode_start = time.time()
        try:
            decode_scale_start = time.time()
            extrinsic = substrate.decode_scale(
                "Extrinsic",
                ScaleBytes(extrinsic_hex)
            )
            decode_scale_time = (time.time() - decode_scale_start) * 1000

            call = extrinsic["call"]

            call_module = call["call_module"]
            call_function = call["call_function"]

            if call_module != "SubtensorModule":
                decode_time = (time.time() - decode_start) * 1000
                logger.debug(f"⏱️ _decode_extrinsic: {decode_time:.2f}ms (decode_scale: {decode_scale_time:.2f}ms) - filtered: wrong module")
                return None

            if call_function not in ("add_stake", "add_stake_limit"):
                decode_time = (time.time() - decode_start) * 1000
                logger.debug(f"⏱️ _decode_extrinsic: {decode_time:.2f}ms (decode_scale: {decode_scale_time:.2f}ms) - filtered: wrong function")
                return None

            args = {
                arg["name"]: arg["value"]
                for arg in call["call_args"]
            }

            netuid = int(args.get("netuid", -1))

            amount = args.get("amount_staked")

            if amount is None:
                decode_time = (time.time() - decode_start) * 1000
                logger.debug(f"⏱️ _decode_extrinsic: {decode_time:.2f}ms (decode_scale: {decode_scale_time:.2f}ms) - filtered: no amount")
                return None

            amount = float(amount) / 1e9

            if amount < config.min_wallet_stake:
                decode_time = (time.time() - decode_start) * 1000
                logger.debug(f"⏱️ _decode_extrinsic: {decode_time:.2f}ms (decode_scale: {decode_scale_time:.2f}ms) - filtered: amount too low")
                return None
            
            decode_time = (time.time() - decode_start) * 1000
            logger.info(f"⏱️ _decode_extrinsic: {decode_time:.2f}ms (decode_scale: {decode_scale_time:.2f}ms) - netuid: {netuid} amount: {amount}")
            
            return {
                "type": "stake",
                "netuid": netuid,
                "amount": amount,
                "hotkey_ss58": args.get("hotkey"),
                "timestamp": time.time()
            }

        except Exception as e:
            decode_time = (time.time() - decode_start) * 1000
            logger.error(f"⏱️ _decode_extrinsic: {decode_time:.2f}ms - Decode error: {e}")
            return None

    async def _safe_callback(self, callback, data):

        callback_start = time.time()
        callback_name = callback.__name__ if hasattr(callback, '__name__') else str(callback)
        try:
            await callback(data)
            callback_time = (time.time() - callback_start) * 1000
            logger.info(f"⏱️ _safe_callback ({callback_name}): {callback_time:.2f}ms")
        except Exception as e:
            callback_time = (time.time() - callback_start) * 1000
            logger.error(f"⏱️ _safe_callback ({callback_name}): {callback_time:.2f}ms - Callback failure: {e}")

    async def _process_mempool(self):

        process_start = time.time()
        
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
        
        logger.debug(f"⏱️ _process_mempool: Processing {len(pending_extrinsics)} pending extrinsics")

        for idx, extrinsic_hex in enumerate(pending_extrinsics):
            
            extrinsic_start = time.time()
            tx_hash = str(extrinsic_hex)
            
            # Cache check
            cache_check_start = time.time()
            if tx_hash in self.tx_cache:
                if now - self.tx_cache[tx_hash] < 1:
                    cache_check_time = (time.time() - cache_check_start) * 1000
                    logger.debug(f"⏱️ Extrinsic {idx+1}/{len(pending_extrinsics)}: cache_check: {cache_check_time:.2f}ms - skipped (recent)")
                    continue
            cache_check_time = (time.time() - cache_check_start) * 1000

            # Capture detection timestamp at the earliest point
            detection_timestamp = time.time()

            # Decode extrinsic
            decode_start = time.time()
            decoded = None

            for substrate in self.substrates:
                decoded = self._decode_extrinsic(substrate, extrinsic_hex)
                if decoded:
                    break
            decode_time = (time.time() - decode_start) * 1000

            if not decoded:
                extrinsic_time = (time.time() - extrinsic_start) * 1000
                logger.debug(f"⏱️ Extrinsic {idx+1}/{len(pending_extrinsics)}: total: {extrinsic_time:.2f}ms (cache_check: {cache_check_time:.2f}ms, decode: {decode_time:.2f}ms) - filtered")
                continue

            self.tx_cache[tx_hash] = now

            # Add detection timestamp to decoded data for latency tracking
            if decoded:
                decoded["detection_timestamp"] = detection_timestamp

            # Execute callbacks
            callback_start = time.time()
            for callback in self.callbacks:
                asyncio.create_task(
                    self._safe_callback(callback, decoded)
                )
            callback_time = (time.time() - callback_start) * 1000
            
            extrinsic_time = (time.time() - extrinsic_start) * 1000
            logger.info(f"⏱️ Extrinsic {idx+1}/{len(pending_extrinsics)}: total: {extrinsic_time:.2f}ms (cache_check: {cache_check_time:.2f}ms, decode: {decode_time:.2f}ms, callback_setup: {callback_time:.2f}ms) - processed")

        cutoff = now - 60
        self.tx_cache = {
            k: v for k, v in self.tx_cache.items()
            if v > cutoff
        }
        
        process_time = (time.time() - process_start) * 1000
        logger.debug(f"⏱️ _process_mempool: total: {process_time:.2f}ms, processed {len([e for e in pending_extrinsics if str(e) not in self.tx_cache or now - self.tx_cache.get(str(e), 0) >= 1])} extrinsics")

    async def start(self):

        await self.connect()

        self.running = True

        logger.info(
            f"Mempool listener started with {len(self.substrates)} nodes"
        )

        poll_interval = max(0.02, config.mempool_check_interval)

        while self.running:

            start = time.time()

            try:
                await self._process_mempool()

            except Exception as e:
                logger.error(f"Mempool loop error: {e}")

            elapsed = time.time() - start

            sleep_time = max(0.005, poll_interval - elapsed)

            await asyncio.sleep(sleep_time)

    async def stop(self):

        self.running = False

        logger.info("Mempool listener stopped")