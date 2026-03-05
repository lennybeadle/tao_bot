'use client'

import { Trade } from '@/lib/api'
import { formatDistanceToNow } from 'date-fns'

interface TradesTableProps {
  trades: Trade[]
}

export default function TradesTable({ trades }: TradesTableProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-400 bg-green-400/10'
      case 'failed':
        return 'text-red-400 bg-red-400/10'
      case 'staked':
        return 'text-yellow-400 bg-yellow-400/10'
      default:
        return 'text-gray-400 bg-gray-400/10'
    }
  }

  const formatAddress = (address: string) => {
    if (!address) return 'N/A'
    return `${address.slice(0, 8)}...${address.slice(-6)}`
  }

  return (
    <div className="bg-dark-surface rounded-lg p-6 border border-dark-border">
      <h2 className="text-2xl font-bold mb-6">Recent Trades</h2>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-dark-border">
              <th className="text-left p-3 text-sm text-gray-400">Time</th>
              <th className="text-left p-3 text-sm text-gray-400">Subnet</th>
              <th className="text-left p-3 text-sm text-gray-400">Wallet</th>
              <th className="text-right p-3 text-sm text-gray-400">Wallet Stake</th>
              <th className="text-right p-3 text-sm text-gray-400">Bot Stake</th>
              <th className="text-right p-3 text-sm text-gray-400">Expected Profit</th>
              <th className="text-right p-3 text-sm text-gray-400">Actual Profit</th>
              <th className="text-center p-3 text-sm text-gray-400">Status</th>
            </tr>
          </thead>
          <tbody>
            {trades.length === 0 ? (
              <tr>
                <td colSpan={8} className="text-center p-8 text-gray-400">
                  No trades yet
                </td>
              </tr>
            ) : (
              trades.map((trade) => (
                <tr
                  key={trade.id}
                  className="border-b border-dark-border hover:bg-dark-bg/50 transition-colors"
                >
                  <td className="p-3 text-sm">
                    {formatDistanceToNow(new Date(trade.timestamp), {
                      addSuffix: true,
                    })}
                  </td>
                  <td className="p-3 text-sm font-mono">{trade.subnet_id}</td>
                  <td className="p-3 text-sm font-mono">
                    {formatAddress(trade.wallet_address)}
                  </td>
                  <td className="p-3 text-sm text-right">
                    {trade.wallet_stake.toFixed(4)} TAO
                  </td>
                  <td className="p-3 text-sm text-right">
                    {trade.bot_stake.toFixed(4)} TAO
                  </td>
                  <td className="p-3 text-sm text-right text-accent-buy">
                    +{trade.expected_profit.toFixed(4)} TAO
                  </td>
                  <td className="p-3 text-sm text-right">
                    {trade.actual_profit !== null ? (
                      <span
                        className={
                          trade.actual_profit >= 0
                            ? 'text-accent-buy'
                            : 'text-accent-sell'
                        }
                      >
                        {trade.actual_profit >= 0 ? '+' : ''}
                        {trade.actual_profit.toFixed(4)} TAO
                      </span>
                    ) : (
                      <span className="text-gray-500">-</span>
                    )}
                  </td>
                  <td className="p-3 text-center">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(
                        trade.status
                      )}`}
                    >
                      {trade.status}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
