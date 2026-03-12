#!/bin/bash
# Linux/macOS script to start the bot
export RUST_LOG=info
echo "Starting TAO Staking Bot..."
cargo run --release --bin start_bot
