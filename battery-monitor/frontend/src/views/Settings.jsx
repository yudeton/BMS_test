import React, { useState, useEffect } from 'react'
import api from '../services/api'

const Settings = () => {
  const [stats, setStats] = useState({
    totalRecords: 0,
    activeAlerts: 0,
    connectedClients: 0,
    uptime: 0
  })

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await api.get('/stats')
        setStats(response.data)
      } catch (error) {
        console.error('Failed to fetch stats:', error)
      }
    }

    fetchStats()
    const interval = setInterval(fetchStats, 10000)
    return () => clearInterval(interval)
  }, [])

  const formatUptime = (seconds) => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    
    return `${days}天 ${hours}小時 ${minutes}分鐘`
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">系統設定</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">系統統計</h2>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600">總記錄數</span>
              <span className="font-semibold">{stats.totalRecords.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">活躍告警</span>
              <span className="font-semibold text-red-600">{stats.activeAlerts}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">連線客戶端</span>
              <span className="font-semibold text-green-600">{stats.connectedClients}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">系統運行時間</span>
              <span className="font-semibold">{formatUptime(stats.uptime)}</span>
            </div>
          </div>
        </div>

        <div className="card">
          <h2 className="text-xl font-semibold mb-4">連線設定</h2>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-600">WebSocket 端口</span>
              <span className="font-semibold">3002</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">API 端口</span>
              <span className="font-semibold">3001</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">自動重連</span>
              <span className="font-semibold text-green-600">已啟用</span>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="text-xl font-semibold mb-4">關於系統</h2>
        <div className="prose prose-sm">
          <p className="text-gray-600">
            電池監控系統 v1.0.0 - 即時監控電池狀態，提供歷史數據分析與告警功能。
          </p>
          <p className="text-gray-600 mt-2">
            支援同一 Wi-Fi 環境下多設備同時監控，未來可擴展至雲端服務。
          </p>
        </div>
      </div>
    </div>
  )
}

export default Settings