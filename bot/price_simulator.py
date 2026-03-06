"""
Price impact simulator for subnet staking
"""
import numpy as np
from typing import Tuple, Optional


class SubnetPool:
    """Simulates subnet TAO/Alpha bonding curve"""
    
    def __init__(self, tao_reserve: float, alpha_reserve: float):
        self.tao = tao_reserve
        self.alpha = alpha_reserve
        self.k = tao_reserve * alpha_reserve  # Constant product
    
    def price(self) -> float:
        """Current price: TAO per Alpha"""
        if self.alpha == 0:
            return 0.0
        return self.tao / self.alpha
    
    def simulate_stake(self, tao_amount: float) -> Tuple[float, float, float]:
        """
        Simulate staking TAO
        
        Returns:
            (new_tao, new_alpha, alpha_received)
        """
        new_tao = self.tao + tao_amount
        new_alpha = self.k / new_tao if new_tao > 0 else 0
        alpha_received = self.alpha - new_alpha
        
        return new_tao, new_alpha, alpha_received
    
    def simulate_unstake(self, alpha_amount: float) -> Tuple[float, float, float]:
        """
        Simulate unstaking Alpha
        
        Returns:
            (new_tao, new_alpha, tao_received)
        """
        new_alpha = self.alpha - alpha_amount
        if new_alpha <= 0:
            return self.tao, self.alpha, 0.0
        
        new_tao = self.k / new_alpha
        tao_received = new_tao - self.tao
        
        return new_tao, new_alpha, tao_received


class PriceSimulator:
    """Simulates bot front-run trades"""
    
    @staticmethod
    def simulate_wallet_stake(
        pool: SubnetPool,
        wallet_stake: float
    ) -> Tuple[float, float]:
        """
        Simulate wallet stake impact
        
        Returns:
            (price_move_percent, new_price)
        """
        initial_price = pool.price()
        
        new_tao, new_alpha, _ = pool.simulate_stake(wallet_stake)
        new_price = new_tao / new_alpha if new_alpha > 0 else 0
        
        price_move = ((new_price - initial_price) / initial_price) * 100 if initial_price > 0 else 0
        
        return price_move, new_price
    
    @staticmethod
    def simulate_bot_trade(
        pool: SubnetPool,
        wallet_stake: float,
        bot_stake: float
    ) -> Tuple[float, float, float]:
        """
        Simulate full bot trade sequence:
        1. Bot stakes
        2. Wallet stakes
        3. Bot unstakes
        
        Returns:
            (expected_profit_tao, price_move_percent, optimal_bot_stake)
        """
        # Step 1: Bot stakes
        tao1 = pool.tao + bot_stake
        alpha1 = pool.k / tao1 if tao1 > 0 else 0
        price_entry = tao1 / alpha1 if alpha1 > 0 else 0
        
        # Step 2: Wallet stakes
        tao2 = tao1 + wallet_stake
        alpha2 = pool.k / tao2 if tao2 > 0 else 0
        price_after_wallet = tao2 / alpha2 if alpha2 > 0 else 0
        
        # Step 3: Bot unstakes (receives TAO based on new price)
        # Bot has alpha1, which is worth more TAO now
        alpha_received = pool.alpha - alpha1
        if alpha_received <= 0:
            return 0.0, 0.0, bot_stake
        
        # Calculate TAO received when unstaking
        temp_pool = SubnetPool(tao2, alpha2)
        _, _, tao_received = temp_pool.simulate_unstake(alpha_received)
        
        # Profit = TAO received - TAO staked
        profit = tao_received - bot_stake
        
        price_move = ((price_after_wallet - pool.price()) / pool.price()) * 100 if pool.price() > 0 else 0
        
        return profit, price_move, bot_stake
    
    @staticmethod
    def find_optimal_stake(
        pool: SubnetPool,
        wallet_stake: float,
        max_bot_stake: float,
        min_profit: float = 0.05
    ) -> Optional[Tuple[float, float, float]]:
        """
        Find optimal bot stake size - ultra-optimized for <5ms execution
        
        Returns:
            (optimal_stake, expected_profit, price_move) or None if not profitable
        """
        # Ultra-fast profitability check (single division)
        if pool.tao <= 0 or pool.alpha <= 0:
            return None
        
        # Quick estimate: price impact must be significant
        impact_ratio = wallet_stake / pool.tao
        if impact_ratio < 0.001:  # Less than 0.1% impact, skip immediately
            return None
        
        # Pre-calculate constants for speed
        k = pool.k  # Constant product
        tao0 = pool.tao
        alpha0 = pool.alpha
        
        best_profit = 0.0
        best_stake = 0.0
        best_price_move = 0.0
        
        # Ultra-fast heuristic: use wallet_stake ratio for initial guess
        # Most profitable is typically 40-60% of wallet stake
        candidate_stakes = [
            wallet_stake * 0.3,  # 30%
            wallet_stake * 0.5,  # 50% - most common optimal
            wallet_stake * 0.7,  # 70%
        ]
        
        # Add fixed sizes if they fit
        if max_bot_stake >= 50:
            candidate_stakes.extend([25.0, 50.0])
        elif max_bot_stake >= 20:
            candidate_stakes.extend([10.0, 20.0])
        else:
            candidate_stakes.extend([5.0, 10.0])
        
        # Filter, sort, and limit to 5 candidates max (for speed)
        candidate_stakes = sorted(
            [s for s in candidate_stakes if 0 < s <= max_bot_stake]
        )[:5]
        
        # Fast simulation loop (optimized math)
        for bot_stake in candidate_stakes:
            # Step 1: Bot stakes (inlined for speed)
            tao1 = tao0 + bot_stake
            alpha1 = k / tao1
            price_entry = tao1 / alpha1
            
            # Step 2: Wallet stakes
            tao2 = tao1 + wallet_stake
            alpha2 = k / tao2
            price_after = tao2 / alpha2
            
            # Step 3: Bot unstakes (receives TAO)
            alpha_received = alpha0 - alpha1
            if alpha_received <= 0:
                continue
            
            # Calculate TAO received (simplified formula)
            tao_received = (alpha_received * tao2) / alpha2
            
            # Profit calculation
            profit = tao_received - bot_stake
            
            if profit > best_profit and profit >= min_profit:
                best_profit = profit
                best_stake = bot_stake
                best_price_move = ((price_after - pool.price()) / pool.price()) * 100
        
        if best_profit > 0:
            return best_stake, best_profit, best_price_move
        
        return None
