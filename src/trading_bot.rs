use anyhow::Result;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio::time::sleep;
use tracing::{debug, error, info};
use subxt::OnlineClient;
use subxt::config::PolkadotConfig;
use crate::config;
use crate::mempool_listener::{MempoolListener, StakeData};
use crate::price_simulator::{PriceSimulator, SubnetPool};
use crate::execution_engine::ExecutionEngine;
use crate::models::Trade;
use crate::database;

pub struct TradingBot {
    mempool_listener: MempoolListener,
    execution_engine: ExecutionEngine,
    subtensor: Arc<RwLock<Option<OnlineClient<PolkadotConfig>>>>,
    running: Arc<RwLock<bool>>,
    daily_trades: Arc<RwLock<i32>>,
    pool_cache: Arc<RwLock<HashMap<i32, (SubnetPool, f64)>>>,
}

impl TradingBot {
    pub fn new() -> Self {
        Self {
            mempool_listener: MempoolListener::new(),
            execution_engine: ExecutionEngine::new(),
            subtensor: Arc::new(RwLock::new(None)),
            running: Arc::new(RwLock::new(false)),
            daily_trades: Arc::new(RwLock::new(0)),
            pool_cache: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub async fn initialize(&self) -> Result<()> {
        info!("Initializing trading bot...");

        // Initialize subtensor connection
        let config = config::get_config();
        let config_guard = config.read().await;
        let rpc_url = &config_guard.subtensor_rpc;

        info!("Connecting to Bittensor network (this may take a moment)...");
        match OnlineClient::from_url(rpc_url).await {
            Ok(client) => {
                *self.subtensor.write().await = Some(client);
                info!("Successfully connected to Bittensor network");
            }
            Err(e) => {
                error!("Failed to initialize subtensor: {}", e);
                return Err(e.into());
            }
        }

        // Initialize execution engine
        self.execution_engine.initialize().await?;

        // Register mempool callback
        let bot = self.clone();
        self.mempool_listener.register_callback(Arc::new(move |stake_data| {
            let bot_clone = bot.clone();
            tokio::spawn(async move {
                bot_clone.handle_stake_detection(stake_data).await;
            });
        })).await;

        // Initialize database
        database::init_db().await?;

        info!("Trading bot initialized");
        Ok(())
    }

    async fn get_subnet_pool(&self, netuid: i32) -> SubnetPool {
        // Check in-memory cache first
        {
            let cache = self.pool_cache.read().await;
            if let Some((pool, cache_time)) = cache.get(&netuid) {
                let now = std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_secs_f64();
                if now - cache_time < 10.0 {
                    return pool.clone();
                }
            }
        }

        // Cache miss - fetch fresh data
        // Placeholder - implement actual pool fetching from chain
        let pool = SubnetPool::new(1000.0, 500.0);
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs_f64();
        
        self.pool_cache.write().await.insert(netuid, (pool.clone(), now));
        pool
    }

    async fn handle_stake_detection(&self, tx_data: StakeData) {
        let netuid = tx_data.netuid;
        let wallet_stake = tx_data.amount;
        let wallet_address = tx_data.hotkey_ss58.clone();

        // Get bot wallet balance
        let bot_balance = self.execution_engine.get_wallet_balance().await;

        if bot_balance.is_none() {
            info!("Could not get bot wallet balance");
            return;
        }

        let bot_balance = bot_balance.unwrap();
        let config = config::get_config();
        let config_guard = config.read().await;
        let min_reserve = config_guard.min_wallet_reserve;

        // Calculate stake amount
        let bot_stake = if bot_balance >= wallet_stake + min_reserve {
            wallet_stake
        } else {
            (bot_balance - min_reserve).max(0.0)
        };

        if bot_stake <= 0.0 {
            info!(
                "⏭️ Skipping trade: insufficient balance (balance: {:.4} TAO, need: {:.4} TAO, reserve: {:.4} TAO)",
                bot_balance, wallet_stake, min_reserve
            );
            return;
        }

        info!(
            "✅ Staking: {:.4} TAO (wallet stake: {:.4} TAO, bot balance: {:.4} TAO)",
            bot_stake, wallet_stake, bot_balance
        );

        // Create trade data
        let trade_id = format!("{}_{}_{}", netuid, wallet_address, 
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs());

        let trade_data = Trade {
            id: None,
            timestamp: chrono::Utc::now(),
            subnet_id: netuid,
            wallet_address,
            wallet_stake,
            bot_stake,
            price_after: None,
            actual_profit: None,
            bot_stake_tx: None,
            bot_unstake_tx: None,
            wallet_tx: None,
            status: "pending".to_string(),
            error_message: None,
        };

        // Execute trade immediately (fire and continue)
        let bot = self.clone();
        tokio::spawn(async move {
            bot.execute_trade(trade_id, trade_data).await;
        });
    }

    async fn execute_trade(&self, trade_id: String, mut trade_data: Trade) {
        let netuid = trade_data.subnet_id;
        let bot_stake = trade_data.bot_stake;

        // Step 1: Bot stakes
        info!("Executing bot stake: {:.4} TAO on subnet {}", bot_stake, netuid);
        
        match self.execution_engine.execute_stake(netuid, bot_stake, Some(trade_id.clone())).await {
            Ok(Some(stake_tx)) => {
                trade_data.bot_stake_tx = Some(stake_tx);
                trade_data.status = "staked".to_string();
            }
            Ok(None) => {
                error!("Bot stake failed");
                trade_data.status = "failed".to_string();
                trade_data.error_message = Some("Bot stake transaction failed".to_string());
                self.record_trade(trade_data).await;
                return;
            }
            Err(e) => {
                error!("Bot stake error: {}", e);
                trade_data.status = "failed".to_string();
                trade_data.error_message = Some(format!("Bot stake error: {}", e));
                self.record_trade(trade_data).await;
                return;
            }
        }

        // Wait for wallet stake to execute (monitor block)
        info!("Waiting for wallet stake to execute...");
        sleep(tokio::time::Duration::from_secs(12)).await;

        // Step 2: Bot unstakes
        info!("Executing bot unstake: {:.4} TAO from subnet {}", bot_stake, netuid);
        
        match self.execution_engine.execute_unstake(netuid, bot_stake, Some(trade_id.clone())).await {
            Ok(Some(unstake_tx)) => {
                trade_data.bot_unstake_tx = Some(unstake_tx);
                trade_data.status = "completed".to_string();
            }
            Ok(None) => {
                error!("Bot unstake failed");
                trade_data.status = "failed".to_string();
                trade_data.error_message = Some("Bot unstake transaction failed".to_string());
            }
            Err(e) => {
                error!("Bot unstake error: {}", e);
                trade_data.status = "failed".to_string();
                trade_data.error_message = Some(format!("Bot unstake error: {}", e));
            }
        }

        // Record trade asynchronously
        self.execution_engine.record_trade_async(trade_data.clone()).await;
        *self.daily_trades.write().await += 1;

        info!("✅ Trade completed: {}", trade_id);
    }

    async fn record_trade(&self, trade_data: Trade) {
        // Record trade in database
        // This would use sqlx to insert
    }

    pub async fn start(&self) -> Result<()> {
        *self.running.write().await = true;
        info!("Starting trading bot...");

        // Start mempool listener
        let listener = self.mempool_listener.clone();
        tokio::spawn(async move {
            if let Err(e) = listener.start().await {
                error!("Mempool listener error: {}", e);
            }
        });

        // Keep main thread alive
        loop {
            sleep(tokio::time::Duration::from_secs(1)).await;
            if !*self.running.read().await {
                break;
            }
        }

        Ok(())
    }

    pub async fn stop(&self) {
        *self.running.write().await = false;
        self.mempool_listener.stop().await;
        info!("Trading bot stopped");
    }
}

impl Clone for TradingBot {
    fn clone(&self) -> Self {
        Self {
            mempool_listener: self.mempool_listener.clone(),
            execution_engine: self.execution_engine.clone(),
            subtensor: Arc::clone(&self.subtensor),
            running: Arc::clone(&self.running),
            daily_trades: Arc::clone(&self.daily_trades),
            pool_cache: Arc::clone(&self.pool_cache),
        }
    }
}
