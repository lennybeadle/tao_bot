use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sqlx::FromRow;

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Trade {
    pub id: Option<i64>,
    pub timestamp: DateTime<Utc>,
    pub subnet_id: i32,
    pub wallet_address: String,
    pub wallet_stake: f64,
    pub bot_stake: f64,
    pub price_after: Option<f64>,
    pub actual_profit: Option<f64>,
    pub bot_stake_tx: Option<String>,
    pub bot_unstake_tx: Option<String>,
    pub wallet_tx: Option<String>,
    pub status: String,
    pub error_message: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Wallet {
    pub id: Option<i64>,
    pub address: String,
    pub total_stakes: i32,
    pub total_staked_amount: f64,
    pub avg_stake_size: f64,
    pub avg_price_impact: f64,
    pub last_seen: DateTime<Utc>,
    pub is_tracked: bool,
    pub is_allowed: bool,
    pub preferred_subnets: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct SubnetPool {
    pub id: Option<i64>,
    pub subnet_id: i32,
    pub tao_reserve: f64,
    pub alpha_reserve: f64,
    pub current_price: f64,
    pub last_updated: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct MonitoredSubnet {
    pub id: Option<i64>,
    pub subnet_id: i32,
    pub created_at: DateTime<Utc>,
}
