
interface RegionData {
  sales_volume: number
  sales_count: number
  demand_trend: string
  staffing_recommendation: string
  marketing_priority: string
}

interface HeatmapProps {
  data: Record<string, RegionData>
}

export function OperationsHeatmap({ data }: HeatmapProps) {
  const regions = ['North', 'East', 'South', 'West']
  
  // Find maximum volume to normalize circle sizes
  const volumes = Object.values(data).map(d => d.sales_volume || 0)
  const maxVolume = Math.max(...volumes, 1)

  const getCoordinates = (region: string) => {
    switch (region) {
      case 'North': return { x: 150, y: 50 }
      case 'East': return { x: 250, y: 150 }
      case 'South': return { x: 150, y: 250 }
      case 'West': return { x: 50, y: 150 }
      default: return { x: 150, y: 150 }
    }
  }

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val)
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: '24px', alignItems: 'start' }}>
      {/* Left Bento: Interactive SVG Map */}
      <div className="card" style={{ height: '360px', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', padding: '16px' }}>
        <div style={{ alignSelf: 'flex-start', marginBottom: '16px' }}>
          <h4 style={{ margin: 0, color: 'var(--color-ink)', fontSize: '0.9rem', fontWeight: 600 }}>Geographic Density Distribution</h4>
          <span style={{ fontSize: '0.72rem', color: 'var(--color-muted)' }}>Circle radius scaled by sales volume</span>
        </div>
        
        <svg width="100%" height="260" viewBox="0 0 300 300" style={{ overflow: 'visible' }}>
          {/* Compass grid lines */}
          <line x1="150" y1="20" x2="150" y2="280" stroke="var(--color-rule-2)" strokeWidth="1" strokeDasharray="4 4" />
          <line x1="20" y1="150" x2="280" y2="150" stroke="var(--color-rule-2)" strokeWidth="1" strokeDasharray="4 4" />
          <circle cx="150" cy="150" r="100" fill="none" stroke="var(--color-rule-2)" strokeWidth="1" strokeDasharray="2 4" />
          <circle cx="150" cy="150" r="50" fill="none" stroke="var(--color-rule-2)" strokeWidth="0.5" strokeDasharray="2 4" />

          {/* Render Heatmap Nodes */}
          {regions.map((reg) => {
            const rData = data[reg] || { sales_volume: 0, sales_count: 0, demand_trend: 'STABLE', staffing_recommendation: 'OPTIMAL', marketing_priority: 'LOW' }
            const coords = getCoordinates(reg)
            const ratio = rData.sales_volume / maxVolume
            const radius = 15 + ratio * 35 // maps volume to radius between 15 and 50
            const opacity = 0.15 + ratio * 0.55 // maps volume to opacity

            return (
              <g key={reg} style={{ cursor: 'pointer' }}>
                {/* Glow ring */}
                <circle
                  cx={coords.x}
                  cy={coords.y}
                  r={radius + 8}
                  fill="none"
                  stroke={ratio > 0.6 ? 'var(--color-error)' : 'var(--color-success)'}
                  strokeWidth="1.5"
                  opacity={opacity * 0.4}
                  style={{ transition: 'all 0.3s ease' }}
                />
                {/* Main bubble */}
                <circle
                  cx={coords.x}
                  cy={coords.y}
                  r={radius}
                  fill={ratio > 0.6 ? 'var(--color-error)' : 'var(--color-success)'}
                  opacity={opacity}
                  style={{ transition: 'all 0.3s ease' }}
                />
                {/* Label text */}
                <text
                  x={coords.x}
                  y={coords.y - radius - 8}
                  textAnchor="middle"
                  fill="var(--color-ink)"
                  style={{ fontSize: '0.68rem', fontWeight: 700, fontFamily: 'var(--font-mono)' }}
                >
                  {reg}
                </text>
                <text
                  x={coords.x}
                  y={coords.y + 4}
                  textAnchor="middle"
                  fill="var(--color-ink)"
                  style={{ fontSize: '0.62rem', fontWeight: 600, fontFamily: 'var(--font-mono)' }}
                >
                  {formatCurrency(rData.sales_volume)}
                </text>
              </g>
            )
          })}
        </svg>
      </div>

      {/* Right Bento: Geographic Performance Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        {regions.map((reg) => {
          const rData = data[reg] || { sales_volume: 0, sales_count: 0, demand_trend: 'STABLE', staffing_recommendation: 'OPTIMAL', marketing_priority: 'LOW' }
          const isUnderperforming = rData.marketing_priority === 'HIGH'

          return (
            <div 
              key={reg} 
              className={`card reveal`} 
              style={{ 
                padding: '16px',
                border: isUnderperforming ? '1px solid var(--color-warning)' : '1px solid var(--color-rule)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--color-ink)' }}>{reg} Region</span>
                <span className={`badge ${rData.demand_trend === 'GROWING' ? 'green' : 'amber'}`} style={{ fontSize: '0.58rem' }}>
                  {rData.demand_trend}
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '0.68rem', color: 'var(--color-muted)' }}>Revenue:</span>
                  <span style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--color-ink)', fontFamily: 'var(--font-mono)' }}>
                    {formatCurrency(rData.sales_volume)}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '0.68rem', color: 'var(--color-muted)' }}>Transactions:</span>
                  <span style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--color-ink)', fontFamily: 'var(--font-mono)' }}>
                    {rData.sales_count} tx
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px', borderTop: '1px solid var(--color-rule-2)', paddingTop: '8px' }}>
                  <span style={{ fontSize: '0.68rem', color: 'var(--color-muted)' }}>Staffing:</span>
                  <span style={{ fontSize: '0.68rem', fontWeight: 600, color: rData.staffing_recommendation === 'INCREASE' ? 'var(--color-error)' : 'var(--color-success)' }}>
                    {rData.staffing_recommendation}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '0.68rem', color: 'var(--color-muted)' }}>Marketing priority:</span>
                  <span className={`badge ${isUnderperforming ? 'red' : 'green'}`} style={{ fontSize: '0.58rem', padding: '1px 4px' }}>
                    {rData.marketing_priority}
                  </span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
