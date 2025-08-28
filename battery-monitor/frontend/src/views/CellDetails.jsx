import React, { useState, useEffect } from 'react'
import api from '../services/api'

const CellDetails = () => {
  const [cellData, setCellData] = useState([])

  useEffect(() => {
    const fetchCellData = async () => {
      try {
        const response = await api.get('/cells')
        setCellData(response.data)
      } catch (error) {
        console.error('Failed to fetch cell data:', error)
      }
    }

    fetchCellData()
    const interval = setInterval(fetchCellData, 5000)
    return () => clearInterval(interval)
  }, [])

  const getCellStatus = (voltage) => {
    if (voltage < 3.0) return { status: 'critical', color: 'bg-red-500' }
    if (voltage < 3.2) return { status: 'warning', color: 'bg-yellow-500' }
    if (voltage > 4.2) return { status: 'warning', color: 'bg-yellow-500' }
    return { status: 'normal', color: 'bg-green-500' }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">電池串詳細資訊</h1>
      
      {cellData.length === 0 ? (
        <div className="card text-center py-8">
          <p className="text-gray-500">暫無電池串數據</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {cellData.map((cell, index) => {
            const { status, color } = getCellStatus(cell.voltage)
            return (
              <div key={cell.cell_number || index} className="card">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-semibold">串 {cell.cell_number}</h3>
                  <div className={`w-3 h-3 rounded-full ${color}`} title={status} />
                </div>
                <div className="text-2xl font-bold text-gray-900 mb-1">
                  {cell.voltage.toFixed(3)} V
                </div>
                <div className="text-sm text-gray-500">
                  {cell.voltage < 3.0 && '⚠️ 電壓過低'}
                  {cell.voltage > 4.2 && '⚠️ 電壓過高'}
                  {cell.voltage >= 3.0 && cell.voltage <= 4.2 && '✅ 正常'}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default CellDetails