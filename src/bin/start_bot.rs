use anyhow::Result;
use tao_bot::trading_bot::TradingBot;
use tracing::{error, info};

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    let bot = TradingBot::new();

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
