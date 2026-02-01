import React from 'react'

export default function AgentBrain({status}:any){
  const log = status?.thinking_log ?? ['Ingesting telemetry: Success rate dropped to 89.2% on Gateway-Alpha. Latency spike detected: 287ms (baseline: 125ms).']
  const nrv = status?.nrv ?? 11971
  const confidence = status?.confidence ?? 94.2
  const lastUpdate = status?.timestamp ? new Date(status.timestamp).toLocaleTimeString() : 'n/a'

  return (
    <div>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start'}}>
        <div style={{flex:1, minWidth:320}}>
          <div className="small">Agent's Brain <span style={{marginLeft:8,color:'var(--muted)'}}>(REASON & DECIDE)</span></div>
          <div style={{marginTop:8}}>
            <div className="card" style={{padding:18,background:'rgba(255,255,255,0.02)',minHeight:220}}>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
                <div className="small">Thinking Log</div>
                <div className="small" style={{color:'var(--muted)'}}>Updated: {lastUpdate}</div>
              </div>
              <div style={{marginTop:12,fontSize:15,lineHeight:1.4,fontWeight:600}}>{log[0]}</div>
            </div>
          </div>
        </div>

        <div style={{width:220}}>
          <div className="small">NRV Calculator</div>
          <div className="card" style={{padding:12,marginTop:8}}>
            <div style={{display:'flex',justifyContent:'space-between'}}>
              <div className="small">Success Lift</div>
              <div style={{color:'#34d399'}}>+12,400</div>
            </div>
            <div style={{display:'flex',justifyContent:'space-between'}}>
              <div className="small">Cost</div>
              <div className="negative">-$340</div>
            </div>
            <div style={{display:'flex',justifyContent:'space-between'}}>
              <div className="small">Latency Penalty</div>
              <div className="negative">-$89</div>
            </div>
            <hr style={{border:'none',borderTop:'1px solid rgba(255,255,255,0.03)',margin:'8px 0'}} />
            <div style={{display:'flex',justifyContent:'space-between',fontWeight:700}}>
              <div>Net Recovery Value</div>
              <div style={{color:'#34d399'}}>${nrv.toLocaleString('en-US')}</div>
            </div>
          </div>

          <div style={{marginTop:10}}>
            <div className="small">Confidence Meter</div>
            <div className="card" style={{padding:8,marginTop:8}}>
              <div style={{background:'rgba(255,255,255,0.03)',borderRadius:6,height:12,overflow:'hidden'}}>
                <div style={{height:12,width:`${confidence}%`,background:'linear-gradient(90deg,#34d399,#10b981)'}} />
              </div>
              <div className="small" style={{marginTop:6}}>{confidence}%</div>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}