'use client'

import { Trade } from '@/lib/api'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'

interface DashboardProps {
  trades: Trade[]
}

export default function Dashboard({ trades }: DashboardProps) {
  // Prepare profit chart data
  const profitData = trades
    .filter((t) => t.actual_profit !== null)
    .slice(-20)
    .map((t, index) => ({
      name: `Trade ${t.id}`,
      profit: t.actual_profit || 0,
      expected: t.expected_profit,
    }))

  // Prepare daily profit data
  const dailyData = trades.reduce((acc: any, trade) => {
    const date = new Date(trade.timestamp).toLocaleDateString()
    if (!acc[date]) {
      acc[date] = { date, profit: 0, count: 0 }
    }
    if (trade.actual_profit !== null) {
      acc[date].profit += trade.actual_profit
      acc[date].count += 1
    }
    return acc
  }, {})

  const dailyChartData = Object.values(dailyData).slice(-7)

  return (
    <div className="bg-dark-surface rounded-lg p-6 border border-dark-border">
      <h2 className="text-2xl font-bold mb-6">Performance Charts</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h3 className="text-lg font-semibold mb-4">Recent Trade Profit</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={profitData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
              <XAxis dataKey="name" stroke="#666" />
              <YAxis stroke="#666" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1a1a1a',
                  border: '1px solid #2a2a2a',
                  borderRadius: '8px',
                }}
              />
              <Line
                type="monotone"
                dataKey="profit"
                stroke="#00d4aa"
                strokeWidth={2}
                name="Actual Profit"
              />
              <Line
                type="monotone"
                dataKey="expected"
                stroke="#666"
                strokeWidth={1}
                strokeDasharray="5 5"
                name="Expected Profit"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div>
          <h3 className="text-lg font-semibold mb-4">Daily Profit (Last 7 Days)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={dailyChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
              <XAxis dataKey="date" stroke="#666" />
              <YAxis stroke="#666" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1a1a1a',
                  border: '1px solid #2a2a2a',
                  borderRadius: '8px',
                }}
              />
              <Bar dataKey="profit" fill="#00d4aa" name="Profit (TAO)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
