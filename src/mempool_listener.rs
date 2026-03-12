use anyhow::Result;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tokio::time::{sleep, Duration};
use tracing::{error, info, warn};
use subxt::OnlineClient;
use subxt::config::PolkadotConfig;
use crate::config;

pub type StakeCallback = Arc<dyn Fn(StakeData) + Send + Sync>;

#[derive(Debug, Clone)]
pub struct StakeData {
    pub netuid: i32,
    pub amount: f64,
    pub hotkey_ss58: String,
    pub timestamp: f64,
}

pub struct MempoolListener {
    substrates: Arc<RwLock<Vec<OnlineClient<PolkadotConfig>>>>,
    running: Arc<RwLock<bool>>,
    callbacks: Arc<RwLock<Vec<StakeCallback>>>,
    tx_cache: Arc<RwLock<HashMap<String, f64>>>,
    rpc_endpoints: Vec<String>,
}

impl MempoolListener {
    pub fn new() -> Self {
        let config = config::get_config();
        let mut rpc_endpoints = vec![];
        
        // Get config synchronously for initialization
        let rt = tokio::runtime::Runtime::new().unwrap();
        let subtensor_rpc = rt.block_on(async {
            config.read().await.subtensor_rpc.clone()
        });
        
        rpc_endpoints.push(subtensor_rpc);
        rpc_endpoints.push("wss://entrypoint-finney.opentensor.ai:443".to_string());
        rpc_endpoints.push("wss://archivelb-finney.opentensor.ai:443".to_string());

        Self {
            substrates: Arc::new(RwLock::new(Vec::new())),
            running: Arc::new(RwLock::new(false)),
            callbacks: Arc::new(RwLock::new(Vec::new())),
            tx_cache: Arc::new(RwLock::new(HashMap::new())),
            rpc_endpoints,
        }
    }

    pub async fn connect(&self) -> Result<()> {
        for rpc_url in &self.rpc_endpoints {
            if self.substrates.read().await.len() >= 2 {
                break;
            }

            match OnlineClient::from_url(rpc_url).await {
                Ok(client) => {
                    self.substrates.write().await.push(client);
                    info!("Connected to {}", rpc_url);
                }
                Err(e) => {
                    warn!("Failed connecting to {}: {}", rpc_url, e);
                }
            }
        }

        if self.substrates.read().await.is_empty() {
            anyhow::bail!("No RPC nodes available");
        }

        Ok(())
    }

    pub async fn register_callback(&self, callback: StakeCallback) {
        self.callbacks.write().await.push(callback);
    }

    async fn fetch_pending_extrinsics(
        &self,
        client: &OnlineClient<PolkadotConfig>,
    ) -> Vec<String> {
        // Note: SubXT doesn't have direct author_pendingExtrinsics support
        // We'll need to use RPC calls directly
        // This is a simplified version - you may need to adjust based on actual API
        vec![] // Placeholder - implement actual RPC call
    }

    fn decode_extrinsic(&self, extrinsic_hex: &str) -> Option<StakeData> {
        // Decode extrinsic and extract stake information
        // This is a simplified version - actual implementation would decode SCALE
        // and check for SubtensorModule::add_stake or add_stake_limit calls
        None // Placeholder - implement actual decoding
    }

    async fn process_extrinsic(&self, extrinsic_hex: String, now: f64) {
        let tx_hash = extrinsic_hex.clone();
        
        // Cache check
        {
            let cache = self.tx_cache.read().await;
            if let Some(&cached_time) = cache.get(&tx_hash) {
                if now - cached_time < 1.0 {
                    return;
                }
            }
        }

        // Decode extrinsic
        let decoded = self.decode_extrinsic(&extrinsic_hex);
        
        if let Some(stake_data) = decoded {
            // Update cache
            self.tx_cache.write().await.insert(tx_hash, now);
            
            // Execute callbacks
            let callbacks = self.callbacks.read().await;
            for callback in callbacks.iter() {
                callback(stake_data.clone());
            }
        }
    }

    async fn process_mempool(&self) -> Result<()> {
        let substrates = self.substrates.read().await.clone();
        let mut pending_extrinsics = Vec::new();

        for substrate in &substrates {
            let extrinsics = self.fetch_pending_extrinsics(substrate).await;
            pending_extrinsics.extend(extrinsics);
        }

        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs_f64();

        for extrinsic_hex in pending_extrinsics {
            let listener = self.clone();
            tokio::spawn(async move {
                listener.process_extrinsic(extrinsic_hex, now).await;
            });
        }
        
        Ok(())
    }

    pub async fn start(&self) -> Result<()> {
        self.connect().await?;
        *self.running.write().await = true;

        info!(
            "Mempool listener started with {} nodes",
            self.substrates.read().await.len()
        );

        let config = config::get_config();
        let poll_interval = {
            let config_guard = config.read().await;
            Duration::from_secs_f64(
                config_guard.mempool_check_interval.max(0.02)
            )
        };

        while *self.running.read().await {
            if let Err(e) = self.process_mempool().await {
                error!("Mempool loop error: {}", e);
            }

            sleep(poll_interval).await;
        }

        Ok(())
    }

    pub async fn stop(&self) {
        *self.running.write().await = false;
        info!("Mempool listener stopped");
    }
}

impl Clone for MempoolListener {
    fn clone(&self) -> Self {
        Self {
            substrates: Arc::clone(&self.substrates),
            running: Arc::clone(&self.running),
            callbacks: Arc::clone(&self.callbacks),
            tx_cache: Arc::clone(&self.tx_cache),
            rpc_endpoints: self.rpc_endpoints.clone(),
        }
    }
}
