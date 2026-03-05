'use client'

import { Stats as StatsType } from '@/lib/api'
import { formatDistanceToNow } from 'date-fns'

interface StatsProps {
  stats: StatsType | null
}

export default function Stats({ stats }: StatsProps) {
  if (!stats) {
    return (
      <div className="bg-dark-surface rounded-lg p-6 border border-dark-border">
        <div className="text-gray-400">Loading statistics...</div>
      </div>
    )
  }

  const statCards = [
    {
      label: 'Total Trades',
      value: stats.total_trades,
      color: 'text-blue-400',
    },
    {
      label: 'Successful Trades',
      value: stats.successful_trades,
      color: 'text-green-400',
    },
    {
      label: 'Total Profit',
      value: `${stats.total_profit.toFixed(4)} TAO`,
      color: 'text-accent-buy',
    },
    {
      label: 'Avg Profit/Trade',
      value: `${stats.avg_profit_per_trade.toFixed(4)} TAO`,
      color: 'text-yellow-400',
    },
    {
      label: 'Trades Today',
      value: stats.trades_today,
      color: 'text-purple-400',
    },
    {
      label: 'Profit Today',
      value: `${stats.profit_today.toFixed(4)} TAO`,
      color: 'text-accent-buy',
    },
  ]

  return (
    <div className="bg-dark-surface rounded-lg p-6 border border-dark-border">
      <h2 className="text-2xl font-bold mb-6">Statistics</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {statCards.map((stat, index) => (
          <div key={index} className="bg-dark-bg rounded p-4">
            <div className="text-sm text-gray-400 mb-1">{stat.label}</div>
            <div className={`text-2xl font-bold ${stat.color}`}>
              {stat.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
