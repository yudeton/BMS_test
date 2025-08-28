import React from 'react'
import { formatDistanceToNow } from 'date-fns'
import { zhTW } from 'date-fns/locale'

const AlertList = ({ alerts = [] }) => {
  if (alerts.length === 0) {
    return (
      <div className="text-center text-gray-500 py-4">
        目前沒有告警
      </div>
    )
  }

  const getSeverityStyle = (severity) => {
    switch (severity) {
      case 'critical':
        return 'alert-critical'
      case 'warning':
        return 'alert-warning'
      case 'info':
        return 'alert-info'
      default:
        return 'alert-info'
    }
  }

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'critical':
        return '🚨'
      case 'warning':
        return '⚠️'
      case 'info':
        return 'ℹ️'
      default:
        return 'ℹ️'
    }
  }

  return (
    <div className="space-y-2 max-h-64 overflow-y-auto">
      {alerts.map((alert, index) => (
        <div key={index} className={`rounded-md ${getSeverityStyle(alert.severity)}`}>
          <div className="flex items-start">
            <span className="mr-2 text-lg">{getSeverityIcon(alert.severity)}</span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">{alert.message}</p>
              {alert.value && (
                <p className="text-xs opacity-75 mt-1">
                  數值: {alert.value}
                </p>
              )}
              <p className="text-xs opacity-75 mt-1">
                {formatDistanceToNow(new Date(alert.timestamp || new Date()), {
                  addSuffix: true,
                  locale: zhTW
                })}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default AlertList