use axum::{
    extract::{Path, Query, State},
    http::StatusCode,
    response::Json,
    routing::{get, put},
    Router,
};
use serde::{Deserialize, Serialize};
use sqlx::SqlitePool;
use std::sync::Arc;
use tokio::sync::RwLock;
use tower_http::cors::CorsLayer;
use crate::config;
use crate::database;
use crate::models::{Trade, Wallet, SubnetPool};

#[derive(Serialize, Deserialize)]
struct TradeResponse {
    id: Option<i64>,
    timestamp: String,
    subnet_id: i32,
    wallet_address: String,
    wallet_stake: f64,
    bot_stake: f64,
    price_after: Option<f64>,
    actual_profit: Option<f64>,
    bot_stake_tx: Option<String>,
    bot_unstake_tx: Option<String>,
    wallet_tx: Option<String>,
    status: String,
    error_message: Option<String>,
}

#[derive(Serialize, Deserialize)]
struct WalletResponse {
    id: Option<i64>,
    address: String,
    total_stakes: i32,
    total_staked_amount: f64,
    avg_stake_size: f64,
    avg_price_impact: f64,
    last_seen: String,
    is_tracked: bool,
    is_allowed: bool,
}

#[derive(Serialize, Deserialize)]
struct StatsResponse {
    total_trades: i64,
    successful_trades: i64,
    total_profit: f64,
    avg_profit_per_trade: f64,
    trades_today: i64,
    profit_today: f64,
}

#[derive(Serialize, Deserialize)]
struct ConfigResponse {
    min_wallet_stake: f64,
    max_bot_stake: f64,
    min_expected_profit: f64,
    bot_stake_ratio: f64,
    monitored_subnets: Vec<i32>,
    max_daily_trades: i32,
    max_slippage: f64,
    allowed_wallet_addresses: Vec<String>,
}

#[derive(Deserialize)]
struct UpdateMonitoredSubnetsRequest {
    monitored_subnets: Vec<i32>,
}

#[derive(Deserialize)]
struct SetWalletAllowedRequest {
    address: String,
    is_allowed: bool,
}

pub async fn create_app() -> Router {
    let database_url = config::get_config().read().await.database_url.clone();
    let pool = database::init_db().await.expect("Failed to initialize database");

    Router::new()
        .route("/", get(root))
        .route("/api/trades", get(get_trades))
        .route("/api/trades/:id", get(get_trade))
        .route("/api/stats", get(get_stats))
        .route("/api/wallets", get(get_wallets))
        .route("/api/config", get(get_config_endpoint))
        .route("/api/config/monitored-subnets", put(update_monitored_subnets))
        .route("/api/pools", get(get_pools))
        .route("/api/wallets/allowed", get(get_allowed_wallets))
        .route("/api/wallets/allowed", put(set_wallet_allowed_status))
        .layer(CorsLayer::permissive())
        .with_state(pool)
}

async fn root() -> Json<serde_json::Value> {
    Json(serde_json::json!({"message": "TAO Staking Bot API"}))
}

async fn get_trades(
    State(pool): State<SqlitePool>,
    Query(params): Query<std::collections::HashMap<String, String>>,
) -> Result<Json<Vec<TradeResponse>>, StatusCode> {
    let limit: i64 = params.get("limit").and_then(|s| s.parse().ok()).unwrap_or(100);
    let offset: i64 = params.get("offset").and_then(|s| s.parse().ok()).unwrap_or(0);
    
    let trades = sqlx::query_as::<_, Trade>(
        "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    )
    .bind(limit)
    .bind(offset)
    .fetch_all(&pool)
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let responses: Vec<TradeResponse> = trades
        .into_iter()
        .map(|t| TradeResponse {
            id: t.id,
            timestamp: t.timestamp.to_rfc3339(),
            subnet_id: t.subnet_id,
            wallet_address: t.wallet_address,
            wallet_stake: t.wallet_stake,
            bot_stake: t.bot_stake,
            price_after: t.price_after,
            actual_profit: t.actual_profit,
            bot_stake_tx: t.bot_stake_tx,
            bot_unstake_tx: t.bot_unstake_tx,
            wallet_tx: t.wallet_tx,
            status: t.status,
            error_message: t.error_message,
        })
        .collect();

    Ok(Json(responses))
}

async fn get_trade(
    State(pool): State<SqlitePool>,
    Path(id): Path<i64>,
) -> Result<Json<TradeResponse>, StatusCode> {
    let trade = sqlx::query_as::<_, Trade>(
        "SELECT * FROM trades WHERE id = ?"
    )
    .bind(id)
    .fetch_optional(&pool)
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .ok_or(StatusCode::NOT_FOUND)?;

    Ok(Json(TradeResponse {
        id: trade.id,
        timestamp: trade.timestamp.to_rfc3339(),
        subnet_id: trade.subnet_id,
        wallet_address: trade.wallet_address,
        wallet_stake: trade.wallet_stake,
        bot_stake: trade.bot_stake,
        price_after: trade.price_after,
        actual_profit: trade.actual_profit,
        bot_stake_tx: trade.bot_stake_tx,
        bot_unstake_tx: trade.bot_unstake_tx,
        wallet_tx: trade.wallet_tx,
        status: trade.status,
        error_message: trade.error_message,
    }))
}

async fn get_stats(
    State(pool): State<SqlitePool>,
) -> Result<Json<StatsResponse>, StatusCode> {
    let total_trades: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM trades")
        .fetch_one(&pool)
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
        .unwrap_or(0);

    let successful_trades: i64 = sqlx::query_scalar(
        "SELECT COUNT(*) FROM trades WHERE status = 'completed'"
    )
    .fetch_one(&pool)
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .unwrap_or(0);

    let total_profit: f64 = sqlx::query_scalar(
        "SELECT COALESCE(SUM(actual_profit), 0) FROM trades WHERE actual_profit IS NOT NULL"
    )
    .fetch_one(&pool)
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .unwrap_or(0.0);

    let avg_profit = if successful_trades > 0 {
        total_profit / successful_trades as f64
    } else {
        0.0
    };

    // Today's stats (simplified - would use proper date filtering)
    let trades_today: i64 = sqlx::query_scalar(
        "SELECT COUNT(*) FROM trades WHERE date(timestamp) = date('now')"
    )
    .fetch_one(&pool)
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .unwrap_or(0);

    let profit_today: f64 = sqlx::query_scalar(
        "SELECT COALESCE(SUM(actual_profit), 0) FROM trades WHERE date(timestamp) = date('now') AND actual_profit IS NOT NULL"
    )
    .fetch_one(&pool)
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .unwrap_or(0.0);

    Ok(Json(StatsResponse {
        total_trades,
        successful_trades,
        total_profit,
        avg_profit_per_trade: avg_profit,
        trades_today,
        profit_today,
    }))
}

async fn get_wallets(
    State(pool): State<SqlitePool>,
) -> Result<Json<Vec<WalletResponse>>, StatusCode> {
    let wallets = sqlx::query_as::<_, Wallet>(
        "SELECT * FROM wallets ORDER BY total_staked_amount DESC LIMIT 50"
    )
    .fetch_all(&pool)
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let responses: Vec<WalletResponse> = wallets
        .into_iter()
        .map(|w| WalletResponse {
            id: w.id,
            address: w.address,
            total_stakes: w.total_stakes,
            total_staked_amount: w.total_staked_amount,
            avg_stake_size: w.avg_stake_size,
            avg_price_impact: w.avg_price_impact,
            last_seen: w.last_seen.to_rfc3339(),
            is_tracked: w.is_tracked,
            is_allowed: w.is_allowed,
        })
        .collect();

    Ok(Json(responses))
}

async fn get_config_endpoint() -> Json<ConfigResponse> {
    let config = config::get_config();
    let config_guard = config.read().await;
    
    let monitored_subnets = config_guard.get_monitored_subnets().await;
    let allowed_wallet_addresses = config_guard.get_allowed_wallet_addresses().await;

    Json(ConfigResponse {
        min_wallet_stake: config_guard.min_wallet_stake,
        max_bot_stake: config_guard.max_bot_stake,
        min_expected_profit: config_guard.min_expected_profit,
        bot_stake_ratio: config_guard.bot_stake_ratio,
        monitored_subnets,
        max_daily_trades: config_guard.max_daily_trades,
        max_slippage: config_guard.max_slippage,
        allowed_wallet_addresses,
    })
}

async fn update_monitored_subnets(
    Json(request): Json<UpdateMonitoredSubnetsRequest>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    if !request.monitored_subnets.iter().all(|&s| s > 0) {
        return Err(StatusCode::BAD_REQUEST);
    }

    database::set_monitored_subnets(request.monitored_subnets.clone())
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let config = config::get_config();
    let config_guard = config.read().await;
    config_guard.reload_monitored_subnets().await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(serde_json::json!({
        "success": true,
        "monitored_subnets": request.monitored_subnets
    })))
}

async fn get_pools(
    State(pool): State<SqlitePool>,
) -> Result<Json<Vec<serde_json::Value>>, StatusCode> {
    let pools = sqlx::query_as::<_, SubnetPool>("SELECT * FROM subnet_pools")
        .fetch_all(&pool)
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let responses: Vec<serde_json::Value> = pools
        .into_iter()
        .map(|p| serde_json::json!({
            "subnet_id": p.subnet_id,
            "tao_reserve": p.tao_reserve,
            "alpha_reserve": p.alpha_reserve,
            "current_price": p.current_price,
            "last_updated": p.last_updated.to_rfc3339()
        }))
        .collect();

    Ok(Json(responses))
}

async fn set_wallet_allowed_status(
    Json(request): Json<SetWalletAllowedRequest>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    if request.address.trim().is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }

    let wallet = database::set_wallet_allowed(&request.address.trim(), request.is_allowed)
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let config = config::get_config();
    let config_guard = config.read().await;
    config_guard.reload_allowed_wallet_addresses().await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(serde_json::json!({
        "success": true,
        "wallet": {
            "id": wallet.id,
            "address": wallet.address,
            "is_allowed": wallet.is_allowed
        }
    })))
}

async fn get_allowed_wallets(
    State(pool): State<SqlitePool>,
) -> Result<Json<Vec<serde_json::Value>>, StatusCode> {
    let config = config::get_config();
    let config_guard = config.read().await;
    config_guard.reload_allowed_wallet_addresses().await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let wallets = sqlx::query_as::<_, Wallet>(
        "SELECT * FROM wallets WHERE is_allowed = 1"
    )
    .fetch_all(&pool)
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let responses: Vec<serde_json::Value> = wallets
        .into_iter()
        .map(|w| serde_json::json!({
            "id": w.id,
            "address": w.address,
            "is_allowed": w.is_allowed,
            "total_stakes": w.total_stakes,
            "total_staked_amount": w.total_staked_amount,
            "last_seen": w.last_seen.to_rfc3339()
        }))
        .collect();

    Ok(Json(responses))
}
