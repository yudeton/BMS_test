import React, { useState, useEffect } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Line } from 'react-chartjs-2'
import api from '../services/api'
import { format } from 'date-fns'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

const History = () => {
  const [timeRange, setTimeRange] = useState('1h')
  const [historyData, setHistoryData] = useState([])
  const [loading, setLoading] = useState(false)

  const fetchHistoryData = async (range) => {
    setLoading(true)
    try {
      const response = await api.get(`/history/${range}`)
      setHistoryData(response.data)
    } catch (error) {
      console.error('Failed to fetch history data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHistoryData(timeRange)
  }, [timeRange])

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top'
      },
      title: {
        display: true,
        text: '電池歷史數據'
      }
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: '時間'
        }
      },
      y: {
        display: true,
        title: {
          display: true,
          text: '數值'
        }
      }
    }
  }

  const chartData = {
    labels: historyData.map(item => format(new Date(item.timestamp), 'HH:mm')),
    datasets: [
      {
        label: '電壓 (V)',
        data: historyData.map(item => item.total_voltage),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        yAxisID: 'y'
      },
      {
        label: '電流 (A)',
        data: historyData.map(item => item.current),
        borderColor: 'rgb(16, 185, 129)',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        yAxisID: 'y1'
      },
      {
        label: 'SOC (%)',
        data: historyData.map(item => item.soc),
        borderColor: 'rgb(245, 158, 11)',
        backgroundColor: 'rgba(245, 158, 11, 0.1)',
        yAxisID: 'y2'
      }
    ]
  }

  const timeRanges = [
    { value: '1h', label: '1小時' },
    { value: '24h', label: '24小時' },
    { value: '7d', label: '7天' },
    { value: '30d', label: '30天' }
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">歷史數據</h1>
        <div className="flex space-x-2">
          {timeRanges.map((range) => (
            <button
              key={range.value}
              onClick={() => setTimeRange(range.value)}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                timeRange === range.value
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>

      <div className="card">
        {loading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-2 text-gray-600">載入中...</p>
          </div>
        ) : historyData.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-500">暫無歷史數據</p>
          </div>
        ) : (
          <Line options={chartOptions} data={chartData} />
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold mb-3">統計摘要</h3>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-600">數據點數</span>
              <span className="font-semibold">{historyData.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">時間範圍</span>
              <span className="font-semibold">{timeRanges.find(r => r.value === timeRange)?.label}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default History