import React from 'react'

const MetricCard = ({ title, value, icon, color = 'blue' }) => {
  const colorClasses = {
    blue: 'text-blue-500 bg-blue-50',
    green: 'text-green-500 bg-green-50',
    red: 'text-red-500 bg-red-50',
    yellow: 'text-yellow-500 bg-yellow-50',
    purple: 'text-purple-500 bg-purple-50',
    orange: 'text-orange-500 bg-orange-50'
  }

  return (
    <div className="card">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="metric-label">{title}</p>
          <p className="metric-value mt-2">{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color] || colorClasses.blue}`}>
          <span className="text-2xl">{icon}</span>
        </div>
      </div>
    </div>
  )
}

export default MetricCard