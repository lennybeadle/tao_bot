mod bot;
mod config;
mod execution_engine;
mod mempool_listener;
mod price_simulator;
mod trading_bot;

use anyhow::Result;
use tracing::{info, error};

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    info!("Starting TAO Staking Bot...");

    let bot = trading_bot::TradingBot::new();
    
    match bot.initialize().await {
        Ok(_) => {
            info!("Bot initialized successfully");
            bot.start().await?;
        }
        Err(e) => {
            error!("Failed to initialize bot: {}", e);
            return Err(e);
        }
    }

    Ok(())
}
