# Windows PowerShell script to start the API server
$env:RUST_LOG="info"
Write-Host "Starting TAO Bot API Server..." -ForegroundColor Green
cargo run --release --bin start_api
