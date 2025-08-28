import React, { useState, useEffect } from 'react'
import useWebSocket from '../hooks/useWebSocket'
import MetricCard from '../components/MetricCard'
import AlertList from '../components/AlertList'
import StatusIndicator from '../components/StatusIndicator'
import api from '../services/api'

const Dashboard = () => {
  const { isConnected, lastMessage } = useWebSocket()
  const [realtimeData, setRealtimeData] = useState({
    total_voltage: 0,
    current: 0,
    power: 0,
    soc: 0,
    temperature: null,
    status: 'unknown'
  })
  const [alerts, setAlerts] = useState([])

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const response = await api.get('/realtime')
        if (response.data.realtime) {
          setRealtimeData(response.data.realtime)
        }
        if (response.data.alerts) {
          setAlerts(response.data.alerts)
        }
      } catch (error) {
        console.error('Failed to fetch initial data:', error)
      }
    }

    fetchInitialData()
  }, [])

  useEffect(() => {
    if (lastMessage) {
      if (lastMessage.topic === 'realtime' && lastMessage.data) {
        setRealtimeData(lastMessage.data)
      } else if (lastMessage.topic === 'alerts' && lastMessage.data) {
        setAlerts(prev => [lastMessage.data, ...prev].slice(0, 10))
      }
    }
  }, [lastMessage])

  const getStatusColor = (status) => {
    switch (status) {
      case 'normal': return 'text-green-500'
      case 'warning': return 'text-yellow-500'
      case 'critical': return 'text-red-500'
      default: return 'text-gray-500'
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-gray-900">電池監控儀表板</h1>
        <StatusIndicator connected={isConnected} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="總電壓"
          value={`${realtimeData.total_voltage.toFixed(2)} V`}
          icon="⚡"
          color="blue"
        />
        <MetricCard
          title="電流"
          value={`${realtimeData.current.toFixed(2)} A`}
          icon="↔"
          color={realtimeData.current > 0 ? 'green' : 'orange'}
        />
        <MetricCard
          title="功率"
          value={`${realtimeData.power.toFixed(2)} W`}
          icon="⚙"
          color="purple"
        />
        <MetricCard
          title="SOC"
          value={`${realtimeData.soc.toFixed(1)} %`}
          icon="🔋"
          color={realtimeData.soc > 20 ? 'green' : 'red'}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-xl font-semibold mb-4">系統狀態</h2>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">狀態</span>
              <span className={`font-semibold ${getStatusColor(realtimeData.status)}`}>
                {realtimeData.status.toUpperCase()}
              </span>
            </div>
            {realtimeData.temperature && (
              <div className="flex justify-between">
                <span className="text-gray-600">溫度</span>
                <span className="font-semibold">
                  {realtimeData.temperature.toFixed(1)} °C
                </span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-gray-600">連線狀態</span>
              <span className={`font-semibold ${isConnected ? 'text-green-500' : 'text-red-500'}`}>
                {isConnected ? '已連線' : '已斷線'}
              </span>
            </div>
          </div>
        </div>

        <div className="card">
          <h2 className="text-xl font-semibold mb-4">最近告警</h2>
          <AlertList alerts={alerts} />
        </div>
      </div>
    </div>
  )
}

export default Dashboard