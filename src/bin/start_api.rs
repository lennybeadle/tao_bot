use anyhow::Result;
use tao_bot::api;
use tao_bot::database;
use tracing::info;
use axum::Server;
use std::net::SocketAddr;
use tao_bot::config;

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    // Initialize database
    database::init_db().await?;
    database::init_default_monitored_subnets().await?;

    // Create app
    let app = api::create_app().await;

    // Get config
    let config = config::get_config();
    let config_guard = config.read().await;
    let addr = SocketAddr::from(([0, 0, 0, 0], config_guard.api_port));

    info!("Starting API server on {}", addr);
    Server::bind(&addr)
        .serve(app.into_make_service())
        .await?;

    Ok(())
}
