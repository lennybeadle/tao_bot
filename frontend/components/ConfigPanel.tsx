'use client'

import { useState } from 'react'
import { Config, updateMonitoredSubnets, fetchConfig } from '@/lib/api'

interface ConfigPanelProps {
  config: Config | null
  onConfigUpdate?: () => void
}

export default function ConfigPanel({ config, onConfigUpdate }: ConfigPanelProps) {
  const [editingSubnets, setEditingSubnets] = useState(false)
  const [subnetIds, setSubnetIds] = useState<number[]>(config?.monitored_subnets || [])
  const [newSubnetId, setNewSubnetId] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!config) {
    return (
      <div className="bg-dark-surface rounded-lg p-6 border border-dark-border">
        <div className="text-gray-400">Loading configuration...</div>
      </div>
    )
  }

  const handleAddSubnet = () => {
    const id = parseInt(newSubnetId.trim())
    if (isNaN(id) || id <= 0) {
      setError('Please enter a valid positive subnet ID')
      return
    }
    if (subnetIds.includes(id)) {
      setError('Subnet ID already exists')
      return
    }
    setSubnetIds([...subnetIds, id].sort((a, b) => a - b))
    setNewSubnetId('')
    setError(null)
  }

  const handleRemoveSubnet = (id: number) => {
    setSubnetIds(subnetIds.filter(s => s !== id))
    setError(null)
  }

  const handleSave = async () => {
    if (subnetIds.length === 0) {
      setError('At least one subnet must be monitored')
      return
    }
    
    setSaving(true)
    setError(null)
    
    try {
      await updateMonitoredSubnets(subnetIds)
      setEditingSubnets(false)
      if (onConfigUpdate) {
        onConfigUpdate()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update monitored subnets')
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    setSubnetIds(config.monitored_subnets)
    setEditingSubnets(false)
    setError(null)
    setNewSubnetId('')
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
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-gray-400">Monitored Subnets</div>
            {!editingSubnets && (
              <button
                onClick={() => {
                  setSubnetIds(config.monitored_subnets)
                  setEditingSubnets(true)
                }}
                className="text-sm text-blue-400 hover:text-blue-300"
              >
                Edit
              </button>
            )}
          </div>
          
          {editingSubnets ? (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {subnetIds.map((subnet) => (
                  <span
                    key={subnet}
                    className="px-3 py-1 bg-dark-bg rounded text-sm font-mono flex items-center gap-2"
                  >
                    {subnet}
                    <button
                      onClick={() => handleRemoveSubnet(subnet)}
                      className="text-red-400 hover:text-red-300"
                      type="button"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              
              <div className="flex gap-2">
                <input
                  type="number"
                  value={newSubnetId}
                  onChange={(e) => {
                    setNewSubnetId(e.target.value)
                    setError(null)
                  }}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      handleAddSubnet()
                    }
                  }}
                  placeholder="Subnet ID"
                  className="flex-1 px-3 py-2 bg-dark-bg border border-dark-border rounded text-sm font-mono focus:outline-none focus:border-blue-500"
                  min="1"
                />
                <button
                  onClick={handleAddSubnet}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-sm font-medium"
                  type="button"
                >
                  Add
                </button>
              </div>
              
              {error && (
                <div className="text-sm text-red-400">{error}</div>
              )}
              
              <div className="flex gap-2">
                <button
                  onClick={handleSave}
                  disabled={saving || subnetIds.length === 0}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-sm font-medium"
                  type="button"
                >
                  {saving ? 'Saving...' : 'Save'}
                </button>
                <button
                  onClick={handleCancel}
                  disabled={saving}
                  className="px-4 py-2 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded text-sm font-medium"
                  type="button"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
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
          )}
        </div>
      </div>
    </div>
  )
}
