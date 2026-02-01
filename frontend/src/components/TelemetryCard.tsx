import React from 'react'

function MiniChart({values, color}:any){
  // simple sparkline as svg
  const w = 300, h = 80, pad = 6
  if(!values || values.length===0)return <div className="chart" />
  const max = Math.max(...values)
  const min = Math.min(...values)
  const points = values.map((v:number,i:number)=>{
    const x = pad + (i/(values.length-1))*(w-2*pad)
    const y = pad + (1 - (v-min)/(max-min || 1))*(h-2*pad)
    return `${x},${y}`
  }).join(' ')
  return (
    <svg className="chart" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      <polyline points={points} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export default function TelemetryCard({status}:any){
  // status from /api/status; fallback to generated mock
  const successSeries = status?.success_series ?? Array.from({length:40},(_,i)=>90 + 5*Math.sin(i/3)+Math.random()*2)
  const latencySeries = status?.latency_series ?? Array.from({length:40},(_,i)=>150 + 40*Math.sin(i/5)+Math.random()*6)
  const total = status?.total_volume ?? 247892
  const failRate = status?.fail_rate ?? 3.5
  const gateway = status?.active_gateway ?? 'Gateway-Alpha'

  return (
    <div>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
        <div>
          <div className="small">Live Telemetry <span style={{marginLeft:8,color:'var(--muted)'}}>(OBSERVE)</span></div>
          <div style={{fontSize:12,color:'var(--muted)'}}>Total Volume</div>
          <div className="bigNumber">{total.toLocaleString('en-US')}</div>
        </div>
        <div style={{textAlign:'right'}}>
          <div className="small">Failed Rate</div>
          <div style={{fontWeight:800,color:failRate>5? 'var(--danger)':'#fbbf24'}}>{failRate}%</div>
          <div className="small" style={{marginTop:8}}>Active Gateway</div>
          <div className="small" style={{color:'var(--muted)'}}>{gateway} • Beta</div>
        </div>
      </div>

      <div style={{display:'flex',gap:12,marginTop:12}}>
        <div style={{flex:1}}>
          <div className="small">Success Rate %</div>
          <MiniChart values={successSeries} color="#34d399" />
        </div>
        <div style={{flex:1}}>
          <div className="small">Latency (ms)</div>
          <MiniChart values={latencySeries} color="#60a5fa" />
        </div>
      </div>

    </div>
  )
}
