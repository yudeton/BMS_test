import React from 'react'

const StatusIndicator = ({ connected }) => {
  return (
    <div className="flex items-center space-x-2">
      <div className={`w-3 h-3 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
      <span className="text-sm text-gray-600">
        {connected ? '即時連線' : '連線中斷'}
      </span>
    </div>
  )
}

export default StatusIndicator