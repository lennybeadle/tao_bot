# Windows PowerShell script to start the bot
$env:RUST_LOG="info"
Write-Host "Starting TAO Staking Bot..." -ForegroundColor Green
cargo run --release --bin start_bot
