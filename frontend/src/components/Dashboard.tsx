import React, { useEffect, useState } from 'react'
import TelemetryCard from './TelemetryCard'
import AgentBrain from './AgentBrain'
import InterventionHistory from './InterventionHistory'
import Guardrails from './Guardrails'

export default function Dashboard() {
  const [status, setStatus] = useState<any>(null)
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting')
  const [notification, setNotification] = useState<null | { msg: string, action: string }>(null)
  const [lastInterventionTs, setLastInterventionTs] = useState<string | null>(null)

  useEffect(() => {
    if (status?.intervention_history?.length > 0) {
      const latest = status.intervention_history[status.intervention_history.length - 1]
      if (latest.ts !== lastInterventionTs) {
        setNotification({ msg: `Intervention Detected: ${latest.reason}`, action: latest.action })
        setLastInterventionTs(latest.ts)
        // Auto-hide notification after 10s
        const t = setTimeout(() => setNotification(null), 10000)
        return () => clearTimeout(t)
      }
    }
  }, [status, lastInterventionTs])

  useEffect(() => {
    let ws: WebSocket | null = null
    let reconnectTimer: number | null = null

    function connect() {
      setWsStatus('connecting')
      try {
        ws = new WebSocket('ws://localhost:8765')
        ws.onopen = () => {
          console.log('WS connected')
          setWsStatus('connected')
        }
        ws.onmessage = (msg) => {
          try {
            const json = JSON.parse(msg.data)
            setStatus(json)
          } catch (e) {
            console.warn('ws parse failed', e)
          }
        }
        ws.onclose = () => {
          console.log('WS closed')
          setWsStatus('disconnected')
          reconnectTimer = window.setTimeout(() => connect(), 3000)
        }
        ws.onerror = (e) => {
          console.warn('WS error', e)
        }
      } catch (e) {
        setWsStatus('disconnected')
        reconnectTimer = window.setTimeout(() => connect(), 3000)
      }
    }

    connect()

    async function load() {
      try {
        const res = await fetch('/api/status')
        const json = await res.json()
        setStatus(json)
      } catch (e) {
        console.warn('status fetch failed', e)
      }
    }
    load()

    return () => {
      if (ws) ws.close()
      if (reconnectTimer) window.clearTimeout(reconnectTimer)
    }
  }, [])

  return (
    <div>
      {notification && (
        <div style={{
          position: 'fixed', top: 20, left: '50%', transform: 'translateX(-50%)',
          background: 'var(--accent)', color: '#000', padding: '12px 24px',
          borderRadius: 8, fontWeight: 700, boxShadow: '0 10px 25px -5px rgba(0,0,0,0.3)',
          zIndex: 1000, display: 'flex', alignItems: 'center', gap: 12,
          animation: 'slideDown 0.3s ease-out'
        }}>
          <div style={{ width: 8, height: 8, borderRadius: 99, background: '#000', animation: 'ping 1s infinite' }} />
          <div>{notification.msg} ({notification.action})</div>
          <button onClick={() => setNotification(null)} style={{ background: 'none', border: 'none', color: '#000', fontWeight: 700, cursor: 'pointer', fontSize: 18 }}>×</button>
        </div>
      )}

      <div className="header">
        <div>
          <div className="projectTitle">Sentinel‑Pay</div>
          <div className="small">Agentic Operations Interface</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div className="small">OPERATIONAL</div>
          <div className="small">Uptime: 99.97%</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 10, height: 10, borderRadius: 999, background: wsStatus === 'connected' ? 'var(--accent)' : wsStatus === 'connecting' ? '#f59e0b' : 'var(--danger)' }} />
            <div className="small" style={{ color: 'var(--muted)' }}>{wsStatus}</div>
          </div>
        </div>
      </div>

      <div className="grid">
        <div className="col">
          <div className="card">
            <TelemetryCard status={status} />
          </div>

          <div className="card">
            <InterventionHistory status={status} />
          </div>
        </div>

        <div className="col">
          <div className="card">
            <AgentBrain status={status} />
          </div>

          <div className="card">
            <Guardrails status={status} />
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes slideDown {
          from { transform: translate(-50%, -100%); opacity: 0; }
          to { transform: translate(-50%, 0); opacity: 1; }
        }
        @keyframes ping {
          75%, 100% { transform: scale(2); opacity: 0; }
        }
      `}</style>
    </div>
  )
}
