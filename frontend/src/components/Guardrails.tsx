import React from 'react'

export default function Guardrails({ status }: any) {
  const metrics = status?.safety_metrics ?? null
  const fpr = metrics ? metrics.false_positive_rate : 0.8
  const avgResp = metrics ? metrics.avg_response_time_s : 1.2
  const rollback = metrics ? metrics.rollback_rate : 2.1
  const escalations = metrics ? metrics.human_escalations : 4

  return (
    <div>
      <div className="small">Guardrails & Safety</div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 12 }}>
        <div>
          <div className="small">Guardian Node</div>
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <div style={{ width: 120 }} className="card">
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>Blocked</div>
              <div style={{ fontWeight: 800, color: '#ef4444', marginTop: 6 }}>3</div>
            </div>
            <div style={{ width: 120 }} className="card">
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>Approved</div>
              <div style={{ fontWeight: 800, color: '#34d399', marginTop: 6 }}>47</div>
            </div>
          </div>
        </div>

        <div style={{ width: 240 }}>
          <div className="small">Safety Metrics</div>
          <div style={{ marginTop: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div className="small">False Positive Rate</div>
              <div className="small" style={{ color: 'var(--muted)' }}>{fpr}%</div>
            </div>
            <div style={{ background: 'rgba(255,255,255,0.03)', height: 8, borderRadius: 6, overflow: 'hidden', marginTop: 6 }}>
              <div style={{ height: 8, width: `${Math.min(100, (fpr * 10))}%`, background: '#34d399' }} />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
              <div className="small">Avg Response Time</div>
              <div className="small" style={{ color: 'var(--muted)' }}>{avgResp}s</div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
              <div className="small">Rollback Rate</div>
              <div className="small" style={{ color: 'var(--muted)' }}>{rollback}%</div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
              <div className="small">Human Escalations</div>
              <div className="small" style={{ color: 'var(--muted)' }}>{escalations}</div>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}