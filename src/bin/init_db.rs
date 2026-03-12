use anyhow::Result;
use tao_bot::database;
use tracing::info;

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    info!("Initializing database...");
    database::init_db().await?;
    info!("Initializing default monitored subnets...");
    database::init_default_monitored_subnets().await?;
    info!("Database initialized successfully!");

    Ok(())
}
