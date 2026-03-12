#[derive(Debug, Clone)]
pub struct SubnetPool {
    pub tao: f64,
    pub alpha: f64,
    pub k: f64, // Constant product
}

impl SubnetPool {
    pub fn new(tao_reserve: f64, alpha_reserve: f64) -> Self {
        let k = tao_reserve * alpha_reserve;
        Self {
            tao: tao_reserve,
            alpha: alpha_reserve,
            k,
        }
    }

    pub fn price(&self) -> f64 {
        if self.alpha == 0.0 {
            return 0.0;
        }
        self.tao / self.alpha
    }

    pub fn simulate_stake(&self, tao_amount: f64) -> (f64, f64, f64) {
        let new_tao = self.tao + tao_amount;
        let new_alpha = if new_tao > 0.0 { self.k / new_tao } else { 0.0 };
        let alpha_received = self.alpha - new_alpha;
        (new_tao, new_alpha, alpha_received)
    }

    pub fn simulate_unstake(&self, alpha_amount: f64) -> (f64, f64, f64) {
        let new_alpha = self.alpha - alpha_amount;
        if new_alpha <= 0.0 {
            return (self.tao, self.alpha, 0.0);
        }
        let new_tao = self.k / new_alpha;
        let tao_received = new_tao - self.tao;
        (new_tao, new_alpha, tao_received)
    }
}

pub struct PriceSimulator;

impl PriceSimulator {
    pub fn simulate_wallet_stake(
        pool: &SubnetPool,
        wallet_stake: f64,
    ) -> (f64, f64) {
        let initial_price = pool.price();
        let (new_tao, new_alpha, _) = pool.simulate_stake(wallet_stake);
        let new_price = if new_alpha > 0.0 { new_tao / new_alpha } else { 0.0 };
        let price_move = if initial_price > 0.0 {
            ((new_price - initial_price) / initial_price) * 100.0
        } else {
            0.0
        };
        (price_move, new_price)
    }

    pub fn simulate_bot_trade(
        pool: &SubnetPool,
        wallet_stake: f64,
        bot_stake: f64,
    ) -> (f64, f64, f64) {
        // Step 1: Bot stakes
        let tao1 = pool.tao + bot_stake;
        let alpha1 = if tao1 > 0.0 { pool.k / tao1 } else { 0.0 };
        let price_entry = if alpha1 > 0.0 { tao1 / alpha1 } else { 0.0 };

        // Step 2: Wallet stakes
        let tao2 = tao1 + wallet_stake;
        let alpha2 = if tao2 > 0.0 { pool.k / tao2 } else { 0.0 };
        let price_after_wallet = if alpha2 > 0.0 { tao2 / alpha2 } else { 0.0 };

        // Step 3: Bot unstakes
        let alpha_received = pool.alpha - alpha1;
        if alpha_received <= 0.0 {
            return (0.0, 0.0, bot_stake);
        }

        let temp_pool = SubnetPool::new(tao2, alpha2);
        let (_, _, tao_received) = temp_pool.simulate_unstake(alpha_received);

        let profit = tao_received - bot_stake;
        let price_move = if pool.price() > 0.0 {
            ((price_after_wallet - pool.price()) / pool.price()) * 100.0
        } else {
            0.0
        };

        (profit, price_move, bot_stake)
    }
}
