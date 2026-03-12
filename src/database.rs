use anyhow::Result;
use sqlx::{SqlitePool, Row};
use chrono::Utc;
use crate::models::{MonitoredSubnet, Wallet};
use crate::config;

pub async fn init_db() -> Result<SqlitePool> {
    let database_url = config::get_config().read().await.database_url.clone();
    let pool = SqlitePool::connect(&database_url).await?;
    
    // Create tables
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            subnet_id INTEGER NOT NULL,
            wallet_address TEXT NOT NULL,
            wallet_stake REAL NOT NULL,
            bot_stake REAL NOT NULL,
            price_after REAL,
            actual_profit REAL,
            bot_stake_tx TEXT,
            bot_unstake_tx TEXT,
            wallet_tx TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            error_message TEXT
        )
        "#,
    )
    .execute(&pool)
    .await?;

    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS wallets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT UNIQUE NOT NULL,
            total_stakes INTEGER NOT NULL DEFAULT 0,
            total_staked_amount REAL NOT NULL DEFAULT 0.0,
            avg_stake_size REAL NOT NULL DEFAULT 0.0,
            avg_price_impact REAL NOT NULL DEFAULT 0.0,
            last_seen DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            is_tracked BOOLEAN NOT NULL DEFAULT 1,
            is_allowed BOOLEAN NOT NULL DEFAULT 0,
            preferred_subnets TEXT
        )
        "#,
    )
    .execute(&pool)
    .await?;

    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS subnet_pools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subnet_id INTEGER UNIQUE NOT NULL,
            tao_reserve REAL NOT NULL,
            alpha_reserve REAL NOT NULL,
            current_price REAL NOT NULL,
            last_updated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        "#,
    )
    .execute(&pool)
    .await?;

    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS monitored_subnets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subnet_id INTEGER UNIQUE NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        "#,
    )
    .execute(&pool)
    .await?;

    // Create indexes
    sqlx::query("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
        .execute(&pool)
        .await?;
    sqlx::query("CREATE INDEX IF NOT EXISTS idx_trades_subnet_id ON trades(subnet_id)")
        .execute(&pool)
        .await?;
    sqlx::query("CREATE INDEX IF NOT EXISTS idx_wallets_address ON wallets(address)")
        .execute(&pool)
        .await?;

    Ok(pool)
}

pub async fn get_monitored_subnets() -> Result<Vec<i32>> {
    let database_url = config::get_config().read().await.database_url.clone();
    let pool = SqlitePool::connect(&database_url).await?;
    
    let rows = sqlx::query("SELECT subnet_id FROM monitored_subnets")
        .fetch_all(&pool)
        .await?;
    
    let subnets: Vec<i32> = rows
        .iter()
        .filter_map(|row| row.try_get::<i32, _>("subnet_id").ok())
        .collect();
    
    Ok(subnets)
}

pub async fn set_monitored_subnets(subnet_ids: Vec<i32>) -> Result<()> {
    let database_url = config::get_config().read().await.database_url.clone();
    let pool = SqlitePool::connect(&database_url).await?;
    
    let mut tx = pool.begin().await?;
    
    sqlx::query("DELETE FROM monitored_subnets")
        .execute(&mut *tx)
        .await?;
    
    for subnet_id in subnet_ids {
        sqlx::query("INSERT INTO monitored_subnets (subnet_id, created_at) VALUES (?, ?)")
            .bind(subnet_id)
            .bind(Utc::now())
            .execute(&mut *tx)
            .await?;
    }
    
    tx.commit().await?;
    Ok(())
}

pub async fn init_default_monitored_subnets() -> Result<()> {
    let existing = get_monitored_subnets().await?;
    if existing.is_empty() {
        let default_subnets = config::get_config()
            .read()
            .await
            .get_monitored_subnets()
            .await;
        set_monitored_subnets(default_subnets).await?;
    }
    Ok(())
}

pub async fn get_allowed_wallet_addresses() -> Result<Vec<String>> {
    let database_url = config::get_config().read().await.database_url.clone();
    let pool = SqlitePool::connect(&database_url).await?;
    
    let rows = sqlx::query("SELECT address FROM wallets WHERE is_allowed = 1")
        .fetch_all(&pool)
        .await?;
    
    let addresses: Vec<String> = rows
        .iter()
        .filter_map(|row| row.try_get::<String, _>("address").ok())
        .collect();
    
    Ok(addresses)
}

pub async fn set_wallet_allowed(address: &str, is_allowed: bool) -> Result<Wallet> {
    let database_url = config::get_config().read().await.database_url.clone();
    let pool = SqlitePool::connect(&database_url).await?;
    
    // Try to find existing wallet
    let existing = sqlx::query_as::<_, Wallet>(
        "SELECT * FROM wallets WHERE address = ?"
    )
    .bind(address)
    .fetch_optional(&pool)
    .await?;
    
    if let Some(mut wallet) = existing {
        wallet.is_allowed = is_allowed;
        sqlx::query("UPDATE wallets SET is_allowed = ? WHERE address = ?")
            .bind(is_allowed)
            .bind(address)
            .execute(&pool)
            .await?;
        Ok(wallet)
    } else {
        let wallet = Wallet {
            id: None,
            address: address.to_string(),
            total_stakes: 0,
            total_staked_amount: 0.0,
            avg_stake_size: 0.0,
            avg_price_impact: 0.0,
            last_seen: Utc::now(),
            is_tracked: true,
            is_allowed,
            preferred_subnets: None,
        };
        
        sqlx::query(
            "INSERT INTO wallets (address, is_allowed, last_seen) VALUES (?, ?, ?)"
        )
        .bind(&wallet.address)
        .bind(wallet.is_allowed)
        .bind(wallet.last_seen)
        .execute(&pool)
        .await?;
        
        Ok(wallet)
    }
}
