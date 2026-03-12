use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;
use once_cell::sync::Lazy;
use std::env;

static CONFIG: Lazy<Arc<RwLock<BotConfig>>> = Lazy::new(|| {
    Arc::new(RwLock::new(BotConfig::new()))
});

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BotConfig {
    pub subtensor_rpc: String,
    pub wallet_name: Option<String>,
    pub wallet_hotkey: Option<String>,
    pub wallet_password: Option<String>,
    pub min_wallet_stake: f64,
    pub max_bot_stake: f64,
    pub min_expected_profit: f64,
    pub bot_stake_ratio: f64,
    pub min_wallet_reserve: f64,
    pub max_daily_trades: i32,
    pub max_slippage: f64,
    pub mempool_check_interval: f64,
    pub transaction_timeout: f64,
    pub use_multiple_rpc: bool,
    #[serde(skip)]
    pub monitored_subnets: Arc<RwLock<Vec<i32>>>,
    #[serde(skip)]
    pub allowed_wallet_addresses: Arc<RwLock<Vec<String>>>,
}

impl Default for BotConfig {
    fn default() -> Self {
        Self::new()
    }
}

impl BotConfig {
    pub fn new() -> Self {
        dotenv::dotenv().ok();
        
        let monitored_subnets = Self::get_default_monitored_subnets();
        let allowed_wallet_addresses = Self::get_default_allowed_wallet_addresses();
        
        Self {
            subtensor_rpc: env::var("SUBTENSOR_RPC")
                .unwrap_or_else(|_| "wss://entrypoint-finney.opentensor.ai:443".to_string()),
            wallet_name: env::var("WALLET_NAME").ok(),
            wallet_hotkey: env::var("WALLET_HOTKEY").ok(),
            wallet_password: env::var("WALLET_PASSWORD").ok(),
            min_wallet_stake: env::var("MIN_WALLET_STAKE")
                .unwrap_or_else(|_| "0.001".to_string())
                .parse()
                .unwrap_or(0.001),
            max_bot_stake: env::var("MAX_BOT_STAKE")
                .unwrap_or_else(|_| "100.0".to_string())
                .parse()
                .unwrap_or(100.0),
            min_expected_profit: env::var("MIN_EXPECTED_PROFIT")
                .unwrap_or_else(|_| "0.05".to_string())
                .parse()
                .unwrap_or(0.05),
            bot_stake_ratio: env::var("BOT_STAKE_RATIO")
                .unwrap_or_else(|_| "0.5".to_string())
                .parse()
                .unwrap_or(0.5),
            min_wallet_reserve: env::var("MIN_WALLET_RESERVE")
                .unwrap_or_else(|_| "0.02".to_string())
                .parse()
                .unwrap_or(0.02),
            max_daily_trades: env::var("MAX_DAILY_TRADES")
                .unwrap_or_else(|_| "50".to_string())
                .parse()
                .unwrap_or(50),
            max_slippage: env::var("MAX_SLIPPAGE")
                .unwrap_or_else(|_| "0.05".to_string())
                .parse()
                .unwrap_or(0.05),
            mempool_check_interval: env::var("MEMPOOL_CHECK_INTERVAL")
                .unwrap_or_else(|_| "0.05".to_string())
                .parse()
                .unwrap_or(0.05),
            transaction_timeout: env::var("TRANSACTION_TIMEOUT")
                .unwrap_or_else(|_| "30.0".to_string())
                .parse()
                .unwrap_or(30.0),
            use_multiple_rpc: env::var("USE_MULTIPLE_RPC")
                .unwrap_or_else(|_| "true".to_string())
                .parse()
                .unwrap_or(true),
            monitored_subnets: Arc::new(RwLock::new(monitored_subnets)),
            allowed_wallet_addresses: Arc::new(RwLock::new(allowed_wallet_addresses)),
        }
    }

    fn get_default_monitored_subnets() -> Vec<i32> {
        env::var("MONITORED_SUBNETS")
            .unwrap_or_else(|_| "46,19,8".to_string())
            .split(',')
            .filter_map(|s| s.trim().parse().ok())
            .collect()
    }

    fn get_default_allowed_wallet_addresses() -> Vec<String> {
        env::var("ALLOWED_WALLET_ADDRESSES")
            .unwrap_or_else(|_| "".to_string())
            .split(',')
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .collect()
    }

    pub async fn reload_monitored_subnets(&self) -> anyhow::Result<()> {
        // Reload from environment variable
        *self.monitored_subnets.write().await = Self::get_default_monitored_subnets();
        Ok(())
    }

    pub async fn reload_allowed_wallet_addresses(&self) -> anyhow::Result<()> {
        // Reload from environment variable
        *self.allowed_wallet_addresses.write().await = Self::get_default_allowed_wallet_addresses();
        Ok(())
    }

    pub async fn get_monitored_subnets(&self) -> Vec<i32> {
        self.monitored_subnets.read().await.clone()
    }

    pub async fn get_allowed_wallet_addresses(&self) -> Vec<String> {
        self.allowed_wallet_addresses.read().await.clone()
    }
}

pub fn get_config() -> Arc<RwLock<BotConfig>> {
    CONFIG.clone()
}
