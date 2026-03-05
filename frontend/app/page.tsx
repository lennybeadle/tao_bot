'use client'

import { useEffect, useState } from 'react'
import Dashboard from '@/components/Dashboard'
import Stats from '@/components/Stats'
import TradesTable from '@/components/TradesTable'
import ConfigPanel from '@/components/ConfigPanel'
import { fetchStats, fetchTrades, fetchConfig } from '@/lib/api'

export default function Home() {
  const [stats, setStats] = useState<any>(null)
  const [trades, setTrades] = useState<any[]>([])
  const [config, setConfig] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      setError(null)
      const [statsData, tradesData, configData] = await Promise.all([
        fetchStats(),
        fetchTrades(50),
        fetchConfig(),
      ])
      setStats(statsData)
      setTrades(tradesData)
      setConfig(configData)
      setLoading(false)
    } catch (error: any) {
      console.error('Error loading data:', error)
      setError('Failed to connect to API. Make sure the API server is running.')
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-bg flex items-center justify-center">
        <div className="text-white text-xl">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-dark-bg flex items-center justify-center">
        <div className="text-red-400 text-xl">{error}</div>
      </div>
    )
  }

  return (
    <main className="min-h-screen bg-dark-bg text-white p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-4xl font-bold">TAO Staking Bot Dashboard</h1>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
            <span className="text-sm text-gray-400">Connected</span>
          </div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <div className="lg:col-span-2">
            <Stats stats={stats} />
          </div>
          <div>
            <ConfigPanel config={config} />
          </div>
        </div>

        {trades.length > 0 && (
          <div className="mb-8">
            <Dashboard trades={trades} />
          </div>
        )}

        <div>
          <TradesTable trades={trades} />
        </div>
      </div>
    </main>
  )
}
