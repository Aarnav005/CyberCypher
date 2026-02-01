import React from 'react'

export default function InterventionHistory({ status }: any) {
  const rows = status?.intervention_history ?? []

  return (
    <div>
      <div className="small">Intervention History <span style={{ marginLeft: 8, color: 'var(--muted)' }}>(ACT & LEARN)</span></div>
      <div className="list" style={{ marginTop: 12 }}>
        {rows.length === 0 && <div className="small" style={{ color: 'var(--muted)', textAlign: 'center', padding: '20px 0' }}>No interventions recorded yet.</div>}
        {rows.map((r: any, i: number) => (
          <div className="listItem" key={i}>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ fontWeight: 700 }}>{r.action}</div>
              <div className="small">{r.reason}</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div className="small">{r.ts}</div>
              <div style={{ marginTop: 6 }}>{r.result}</div>
              <div className="small" style={{ marginTop: 6, color: '#34d399' }}>{r.rate}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}