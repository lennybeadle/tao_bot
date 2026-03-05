'use client'

import { Config } from '@/lib/api'

interface ConfigPanelProps {
  config: Config | null
}

export default function ConfigPanel({ config }: ConfigPanelProps) {
  if (!config) {
    return (
      <div className="bg-dark-surface rounded-lg p-6 border border-dark-border">
        <div className="text-gray-400">Loading configuration...</div>
      </div>
    )
  }

  return (
    <div className="bg-dark-surface rounded-lg p-6 border border-dark-border">
      <h2 className="text-2xl font-bold mb-6">Configuration</h2>
      <div className="space-y-4">
        <div>
          <div className="text-sm text-gray-400 mb-1">Min Wallet Stake</div>
          <div className="text-lg font-mono">{config.min_wallet_stake} TAO</div>
        </div>
        <div>
          <div className="text-sm text-gray-400 mb-1">Max Bot Stake</div>
          <div className="text-lg font-mono">{config.max_bot_stake} TAO</div>
        </div>
        <div>
          <div className="text-sm text-gray-400 mb-1">Min Expected Profit</div>
          <div className="text-lg font-mono">{config.min_expected_profit} TAO</div>
        </div>
        <div>
          <div className="text-sm text-gray-400 mb-1">Bot Stake Ratio</div>
          <div className="text-lg font-mono">{(config.bot_stake_ratio * 100).toFixed(0)}%</div>
        </div>
        <div>
          <div className="text-sm text-gray-400 mb-1">Max Daily Trades</div>
          <div className="text-lg font-mono">{config.max_daily_trades}</div>
        </div>
        <div>
          <div className="text-sm text-gray-400 mb-1">Max Slippage</div>
          <div className="text-lg font-mono">{(config.max_slippage * 100).toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-sm text-gray-400 mb-1">Monitored Subnets</div>
          <div className="flex flex-wrap gap-2 mt-2">
            {config.monitored_subnets.map((subnet) => (
              <span
                key={subnet}
                className="px-3 py-1 bg-dark-bg rounded text-sm font-mono"
              >
                {subnet}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
