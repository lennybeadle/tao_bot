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