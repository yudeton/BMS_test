import { useEffect, useRef, useState, useCallback } from 'react'
import toast from 'react-hot-toast'

const useWebSocket = (url = 'ws://localhost:3002') => {
  const ws = useRef(null)
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState(null)
  const reconnectTimeoutId = useRef(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 10
  const reconnectDelay = 5000

  const connect = useCallback(() => {
    try {
      ws.current = new WebSocket(url)

      ws.current.onopen = () => {
        setIsConnected(true)
        reconnectAttempts.current = 0
        toast.success('已連線到監控系統')
        
        ws.current.send(JSON.stringify({
          type: 'subscribe',
          topics: ['realtime', 'cells', 'alerts']
        }))
      }

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          setLastMessage(data)
        } catch (error) {
          console.error('Failed to parse message:', error)
        }
      }

      ws.current.onclose = () => {
        setIsConnected(false)
        toast.error('連線已斷開')
        
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectTimeoutId.current = setTimeout(() => {
            reconnectAttempts.current++
            toast('嘗試重新連線...')
            connect()
          }, reconnectDelay)
        } else {
          toast.error('無法連線到監控系統')
        }
      }

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    } catch (error) {
      console.error('Failed to connect:', error)
      setIsConnected(false)
    }
  }, [url])

  const disconnect = useCallback(() => {
    if (ws.current) {
      ws.current.close()
    }
    if (reconnectTimeoutId.current) {
      clearTimeout(reconnectTimeoutId.current)
    }
  }, [])

  const sendMessage = useCallback((message) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message))
      return true
    }
    return false
  }, [])

  useEffect(() => {
    connect()
    
    const heartbeatInterval = setInterval(() => {
      sendMessage({ type: 'ping' })
    }, 30000)

    return () => {
      clearInterval(heartbeatInterval)
      disconnect()
    }
  }, [connect, disconnect, sendMessage])

  return {
    isConnected,
    lastMessage,
    sendMessage,
    reconnect: connect
  }
}

export default useWebSocket