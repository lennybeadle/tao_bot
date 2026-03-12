#!/bin/bash
# Linux/macOS script to start the API server
export RUST_LOG=info
echo "Starting TAO Bot API Server..."
cargo run --release --bin start_api
