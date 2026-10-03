import { useState, useEffect, useCallback } from 'react'
import './index.css'
import {
  getDashboard, getHealth, getAlerts, getTimeline,
  getRevenueForecast, getCashflowForecast,
  getAgents,
  simulate, sendChat, getExecutiveBrief,
  getCustomerRisk, getSupplierRisk, getPricing,
  getDecisionHistory,
  uploadFile, uploadSampleDoc,
  getMaterials, getProducts, createMaterial, updateMaterial,
  deleteMaterial, getMaterialPriceHistory, createPriceHistory,
  getMaterialForecast, getStrategyBrief, getMaterialBuyingAdvice,
} from './api'
import { OperationsHeatmap } from './components/OperationsHeatmap'
import {
  LayoutDashboard,
  TrendingUp,
  ShieldAlert,
  Bot,
  MessageSquare,
  FileText,
  History,
  Activity,
  ArrowUpRight,
  DollarSign,
  Users,
  Truck,
  Play,
  Send,
  CheckCircle2,
  Calendar,
  Sparkles,
  Sliders,
  DollarSign as MoneyIcon,
  Upload,
  Sun,
  Moon,
} from 'lucide-react'

// ─── Types ────────────────────────────────────────────────────
type Page = 'dashboard' | 'forecast' | 'risk' | 'agents' | 'simulate' | 'chat' | 'brief' | 'history' | 'upload' | 'materials' | 'strategy'

// ─── Helpers ──────────────────────────────────────────────────
const fmt = (n: number) =>
  n >= 1_000_000 ? `$${(n / 1_000_000).toFixed(2)}M`
    : n >= 1_000 ? `$${(n / 1_000).toFixed(1)}K`
      : `$${n.toFixed(2)}`

const pct = (n: number) => `${(n * 100).toFixed(0)}%`

const AGENT_META: Record<string, { icon: string; color: string; border: string }> = {
  FinanceAgent: { icon: '💰', color: 'rgba(16,185,129,0.08)', border: 'var(--color-success)' },
  OperationsAgent: { icon: '⚙️', color: 'rgba(59,130,246,0.08)', border: 'var(--color-accent)' },
  MarketingAgent: { icon: '📣', color: 'rgba(245,158,11,0.08)', border: 'var(--color-warning)' },
  SupplierAgent: { icon: '🚚', color: 'rgba(139,92,246,0.08)', border: 'oklch(65% 0.16 300)' },
  CustomerAgent: { icon: '👥', color: 'rgba(6,182,212,0.08)', border: 'var(--color-info)' },
  RiskAgent: { icon: '🛡️', color: 'rgba(239,68,68,0.08)', border: 'var(--color-error)' },
}

// ─── Smooth Number Ticker Component (A11y Compliant - Static Mode) ───
function NumberTicker({ value, formatFn = (n: number) => String(n) }: { value: number; formatFn?: (n: number) => string; duration?: number }) {
  return <span className="aria-live-polite">{formatFn(value)}</span>
}

// ─── Inline Sparkline Vector Component ────────────────────────
function Sparkline({ data, color = 'var(--color-accent)' }: { data: number[]; color?: string }) {
  const width = 80
  const height = 24

  const minVal = Math.min(...data)
  const maxVal = Math.max(...data)
  const range = maxVal - minVal || 1

  const getX = (idx: number) => (idx / (data.length - 1)) * width
  const getY = (val: number) => height - 1.5 - ((val - minVal) / range) * (height - 3)

  let path = ''
  data.forEach((val, i) => {
    const x = getX(i)
    const y = getY(val)
    if (i === 0) path += `M ${x} ${y}`
    else path += ` L ${x} ${y}`
  })

  return (
    <svg width={width} height={height} style={{ overflow: 'visible', opacity: 0.75, pointerEvents: 'none' }}>
      <path d={path} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

// ─── Interactive Telemetry Chart Component ───────────────────
function TelemetryChart({ baseValue, confidence, color = 'var(--color-accent)', secondaryColor = 'var(--color-accent-dim)', unit = '$', days = 90 }: { baseValue: number; confidence: number; color?: string; secondaryColor?: string; unit?: string; days?: number }) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)
  const [hoverPos, setHoverPos] = useState({ x: 0, y: 0 })

  type DataPoint = {
    day: number
    value: number
    lower: number
    upper: number
  }
  const pointsCount = 12
  const dataPoints: DataPoint[] = []

  for (let i = 0; i < pointsCount; i++) {
    const progress = i / (pointsCount - 1)
    const trend = baseValue * (0.85 + progress * 0.3)
    const cycle = Math.sin(progress * Math.PI * 2.5) * (baseValue * 0.04)
    const val = trend + cycle
    const uncertaintyRange = (baseValue * 0.14) * (1 - confidence * 0.4) * (1 + progress * 1.3)

    dataPoints.push({
      day: Math.round(progress * days),
      value: val,
      lower: val - uncertaintyRange,
      upper: val + uncertaintyRange,
    })
  }

  const width = 500
  const height = 180
  const paddingX = 45
  const paddingY = 20

  const chartWidth = width - paddingX * 2
  const chartHeight = height - paddingY * 2

  const minVal = Math.min(...dataPoints.map(d => d.lower)) * 0.96
  const maxVal = Math.max(...dataPoints.map(d => d.upper)) * 1.04
  const valRange = maxVal - minVal || 1

  const getX = (index: number) => paddingX + (index / (pointsCount - 1)) * chartWidth
  const getY = (val: number) => paddingY + chartHeight - ((val - minVal) / valRange) * chartHeight

  let linePath = ''
  dataPoints.forEach((d, i) => {
    const x = getX(i)
    const y = getY(d.value)
    if (i === 0) linePath += `M ${x} ${y}`
    else linePath += ` L ${x} ${y}`
  })

  let boundsCoords = ''
  dataPoints.forEach((d, i) => {
    boundsCoords += `${getX(i)},${getY(d.upper)} `
  })
  for (let i = pointsCount - 1; i >= 0; i--) {
    const d = dataPoints[i]
    boundsCoords += `${getX(i)},${getY(d.lower)} `
  }

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement, MouseEvent>) => {
    const svgRect = e.currentTarget.getBoundingClientRect()
    const mouseX = e.clientX - svgRect.left
    const relativeX = (mouseX - paddingX) / chartWidth
    const approxIndex = Math.round(relativeX * (pointsCount - 1))
    const index = Math.max(0, Math.min(pointsCount - 1, approxIndex))

    setHoveredIndex(index)
    setHoverPos({
      x: getX(index),
      y: getY(dataPoints[index].value),
    })
  }

  const handleMouseLeave = () => {
    setHoveredIndex(null)
  }

  const formatTooltipValue = (v: number) => {
    if (unit === '$') return fmt(v)
    return String(v.toFixed(1))
  }

  return (
    <div style={{ position: 'relative', width: '100%', marginTop: 'var(--space-sm)' }}>
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        style={{ overflow: 'visible', cursor: 'crosshair' }}
      >
        {/* Gridlines */}
        {[0, 0.25, 0.5, 0.75, 1].map((p, idx) => {
          const val = minVal + p * valRange
          const y = getY(val)
          return (
            <g key={idx}>
              <line x1={paddingX} y1={y} x2={width - paddingX} y2={y} stroke="var(--color-rule-2)" strokeWidth="1" strokeDasharray="3,3" />
              <text x={paddingX - 8} y={y + 3} textAnchor="end" fill="var(--color-muted)" style={{ fontFamily: 'var(--font-mono)', fontSize: '8px' }}>
                {unit === '$' ? fmt(val) : val.toFixed(0)}
              </text>
            </g>
          )
        })}

        {/* X Axis */}
        {dataPoints.filter((_, i) => i % 3 === 0).map((d, idx) => {
          const x = getX(dataPoints.indexOf(d))
          return (
            <g key={idx}>
              <line x1={x} y1={height - paddingY} x2={x} y2={height - paddingY + 4} stroke="var(--color-rule)" strokeWidth="1" />
              <text x={x} y={height - paddingY + 12} textAnchor="middle" fill="var(--color-muted)" style={{ fontFamily: 'var(--font-mono)', fontSize: '8px' }}>
                T+{d.day}d
              </text>
            </g>
          )
        })}

        {/* Confidence Shading */}
        <polygon points={boundsCoords} fill={secondaryColor} />

        {/* Line */}
        <path d={linePath} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />

        {/* Focus Crosshair */}
        {hoveredIndex !== null && (
          <g>
            <line x1={hoverPos.x} y1={paddingY} x2={hoverPos.x} y2={height - paddingY} stroke="var(--color-rule)" strokeWidth="1" strokeDasharray="2,2" />
            <circle cx={hoverPos.x} cy={hoverPos.y} r="4" fill={color} stroke="var(--color-paper)" strokeWidth="1.5" />
          </g>
        )}
      </svg>

      {/* Dynamic Tooltip Box */}
      {hoveredIndex !== null && (
        <div style={{
          position: 'absolute',
          top: hoverPos.y - 50 < 8 ? 8 : hoverPos.y - 50,
          left: hoverPos.x + 12 > width - 130 ? hoverPos.x - 135 : hoverPos.x + 12,
          background: 'var(--color-paper-3)',
          border: '1px solid var(--color-rule)',
          borderRadius: '4px',
          padding: '4px var(--space-xs)',
          zIndex: 10,
          pointerEvents: 'none',
          boxShadow: 'var(--shadow-card)',
          transition: 'all 80ms var(--ease-out)',
        }}>
          <div style={{ fontSize: '8px', fontFamily: 'var(--font-mono)', color: 'var(--color-muted)', textTransform: 'uppercase', marginBottom: '2px' }}>
            Day T+{dataPoints[hoveredIndex].day} Projection
          </div>
          <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--color-ink)' }}>
            {formatTooltipValue(dataPoints[hoveredIndex].value)}
          </div>
          <div style={{ fontSize: '7.5px', fontFamily: 'var(--font-mono)', color: 'var(--color-muted)', whiteSpace: 'nowrap' }}>
            Range: {formatTooltipValue(dataPoints[hoveredIndex].lower)} - {formatTooltipValue(dataPoints[hoveredIndex].upper)}
          </div>
        </div>
      )}
    </div>
  )
}


// ─── Skeletons ────────────────────────────────────────────────
function DashboardPageSkeleton() {
  return (
    <div className="page-body">
      <div className="bento-grid">
        {/* KPI Metrics */}
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="col-3 metric-tile reveal" style={{ '--i': i } as any}>
            <div className="metric-tile-header">
              <span className="skeleton skeleton-text short" style={{ height: '14px' }} />
              <div className="skeleton skeleton-circle" style={{ width: '14px', height: '14px' }} />
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginTop: 'var(--space-2xs)' }}>
              <div className="skeleton skeleton-value" />
              <div className="skeleton skeleton-sparkline" />
            </div>
          </div>
        ))}

        {/* Row 2: Health telemetry & Alerts */}
        <div className="col-6 row-2 card reveal" style={{ '--i': 4 } as any}>
          <div className="card-header">
            <div>
              <div className="skeleton skeleton-title" style={{ width: '120px' }} />
              <div className="skeleton skeleton-text medium" style={{ width: '180px' }} />
            </div>
            <span className="skeleton" style={{ width: '60px', height: '18px', borderRadius: '4px' }} />
          </div>
          <div className="health-ring-wrap" style={{ margin: 'var(--space-xs) 0', display: 'flex', gap: 'var(--space-md)' }}>
            <div className="skeleton skeleton-circle" style={{ width: '96px', height: '96px', flexShrink: 0 }} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2xs)', flex: 1 }}>
              {[0, 1, 2, 3].map((j) => (
                <div key={j} style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '4px', borderBottom: '1px solid var(--color-rule-2)' }}>
                  <span className="skeleton skeleton-text short" />
                  <span className="skeleton skeleton-text" style={{ width: '50px' }} />
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="col-6 row-2 card reveal" style={{ '--i': 5 } as any}>
          <div className="card-header">
            <div>
              <div className="skeleton skeleton-title" style={{ width: '140px' }} />
              <div className="skeleton skeleton-text medium" style={{ width: '200px' }} />
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2xs)' }}>
            {[0, 1, 2].map((j) => (
              <div key={j} className="alert-item" style={{ border: '1px solid var(--color-rule-2)', padding: '10px' }}>
                <span className="skeleton" style={{ width: '40px', height: '14px', borderRadius: '3px' }} />
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1, marginLeft: '8px' }}>
                  <span className="skeleton skeleton-text medium" />
                  <span className="skeleton skeleton-text long" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Row 3: Event Log & Secondary Metrics */}
        <div className="col-8 card reveal" style={{ '--i': 6 } as any}>
          <div className="card-header">
            <div>
              <div className="skeleton skeleton-title" style={{ width: '120px' }} />
              <div className="skeleton skeleton-text medium" style={{ width: '180px' }} />
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2xs)' }}>
            {[0, 1, 2].map((j) => (
              <div key={j} style={{ display: 'flex', gap: 'var(--space-xs)', padding: '8px 0', borderBottom: '1px solid var(--color-rule-2)' }}>
                <div className="skeleton skeleton-circle" style={{ width: '8px', height: '8px', marginTop: '4px', flexShrink: 0 }} />
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <span className="skeleton skeleton-text short" />
                  <span className="skeleton skeleton-text long" />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="col-4 card reveal" style={{ '--i': 7 } as any}>
          <div className="card-header">
            <div>
              <div className="skeleton skeleton-title" style={{ width: '100px' }} />
              <div className="skeleton skeleton-text medium" style={{ width: '120px' }} />
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-2xs)', height: '100%' }}>
            {[0, 1, 2, 3].map((j) => (
              <div key={j} style={{ background: 'var(--color-paper-3)', padding: 'var(--space-2xs)', borderRadius: 'var(--radius-card)', border: '1px solid var(--color-rule-2)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <span className="skeleton skeleton-text short" />
                <span className="skeleton skeleton-value" style={{ width: '80px', height: '20px' }} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function ForecastPageSkeleton() {
  return (
    <div className="page-body">
      <div className="bento-grid">
        {/* Left Column */}
        <div className="col-6 card reveal" style={{ '--i': 0 } as any}>
          <div className="card-header">
            <div>
              <div className="skeleton skeleton-title" style={{ width: '180px' }} />
              <div className="skeleton skeleton-text medium" style={{ width: '220px' }} />
            </div>
            <span className="skeleton" style={{ width: '80px', height: '18px', borderRadius: '4px' }} />
          </div>
          <div style={{ margin: 'var(--space-xs) 0' }}>
            <div className="skeleton skeleton-value" style={{ width: '200px', height: '36px' }} />
            <div className="skeleton skeleton-text long" style={{ marginTop: '8px' }} />
          </div>
          <div className="confidence-bar" style={{ height: '8px', background: 'var(--color-rule-2)' }}>
            <div className="skeleton" style={{ width: '100%', height: '100%' }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', margin: 'var(--space-xs) 0 4px 0' }}>
            <span className="skeleton skeleton-text short" />
            <span className="skeleton skeleton-text" style={{ width: '120px' }} />
          </div>
          <div className="skeleton" style={{ width: '100%', height: '140px', borderRadius: 'var(--radius-card)' }} />
        </div>

        {/* Right Column */}
        <div className="col-6 card reveal" style={{ '--i': 1 } as any}>
          <div className="card-header">
            <div>
              <div className="skeleton skeleton-title" style={{ width: '160px' }} />
              <div className="skeleton skeleton-text medium" style={{ width: '200px' }} />
            </div>
            <span className="skeleton" style={{ width: '80px', height: '18px', borderRadius: '4px' }} />
          </div>
          <div style={{ margin: 'var(--space-xs) 0' }}>
            <div className="skeleton skeleton-value" style={{ width: '160px', height: '36px' }} />
            <div className="skeleton skeleton-text long" style={{ marginTop: '8px' }} />
          </div>
          <div className="skeleton" style={{ width: '100%', height: '110px', borderRadius: 'var(--radius-card)', marginBottom: 'var(--space-xs)' }} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2xs)' }}>
            {[0, 1, 2].map((j) => (
              <div key={j} style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '4px', borderBottom: '1px solid var(--color-rule-2)' }}>
                <span className="skeleton skeleton-text short" />
                <span className="skeleton skeleton-text" style={{ width: '60px' }} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function RiskPageSkeleton() {
  return (
    <div className="page-body">
      {[0, 1, 2].map((cardIdx) => (
        <div key={cardIdx} className="card reveal" style={{ '--i': cardIdx } as any}>
          <div className="card-header">
            <div>
              <div className="skeleton skeleton-title" style={{ width: '180px' }} />
              <div className="skeleton skeleton-text medium" style={{ width: '220px' }} />
            </div>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                {cardIdx === 0 && (
                  <>
                    <th><span className="skeleton skeleton-text short" /></th>
                    <th><span className="skeleton skeleton-text short" /></th>
                    <th><span className="skeleton skeleton-text short" /></th>
                    <th><span className="skeleton skeleton-text short" /></th>
                    <th><span className="skeleton skeleton-text short" /></th>
                  </>
                )}
                {cardIdx === 1 && (
                  <>
                    <th><span className="skeleton skeleton-text short" /></th>
                    <th><span className="skeleton skeleton-text short" /></th>
                    <th><span className="skeleton skeleton-text short" /></th>
                    <th><span className="skeleton skeleton-text short" /></th>
                    <th><span className="skeleton skeleton-text short" /></th>
                  </>
                )}
                {cardIdx === 2 && (
                  <>
                    <th><span className="skeleton skeleton-text short" /></th>
                    <th><span className="skeleton skeleton-text short" /></th>
                    <th><span className="skeleton skeleton-text short" /></th>
                    <th><span className="skeleton skeleton-text short" /></th>
                    <th><span className="skeleton skeleton-text short" /></th>
                    <th><span className="skeleton skeleton-text short" /></th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {[0, 1, 2].map((rowIdx) => (
                <tr key={rowIdx}>
                  <td><span className="skeleton skeleton-text medium" /></td>
                  <td><span className="skeleton skeleton-text short" style={{ height: '14px', borderRadius: '3px' }} /></td>
                  <td><span className="skeleton skeleton-text short" style={{ height: '14px', borderRadius: '3px' }} /></td>
                  <td><span className="skeleton skeleton-text short" /></td>
                  <td><span className="skeleton skeleton-text long" /></td>
                  {cardIdx === 2 && <td><span className="skeleton skeleton-text short" /></td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  )
}

function AgentsPageSkeleton() {
  return (
    <div className="agent-grid">
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <div className="agent-card reveal" key={i} style={{ '--i': i } as any}>
          <div className="agent-header">
            <div className="skeleton skeleton-circle" style={{ width: '32px', height: '32px', flexShrink: 0 }} />
            <div style={{ flex: 1, marginLeft: '8px' }}>
              <span className="skeleton skeleton-text medium" style={{ height: '14px' }} />
              <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
                <span className="skeleton" style={{ width: '40px', height: '14px', borderRadius: '3px' }} />
                <span className="skeleton" style={{ width: '80px', height: '14px', borderRadius: '3px' }} />
              </div>
            </div>
          </div>
          <div style={{ margin: 'var(--space-xs) 0' }}>
            <span className="skeleton skeleton-text long" />
            <span className="skeleton skeleton-text medium" style={{ marginTop: '4px' }} />
            <span className="skeleton skeleton-text long" style={{ marginTop: '4px' }} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span className="skeleton skeleton-text long" style={{ height: '24px', borderRadius: '4px' }} />
            <span className="skeleton skeleton-text long" style={{ height: '24px', borderRadius: '4px' }} />
          </div>
        </div>
      ))}
    </div>
  )
}

function BriefPageSkeleton() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
      <div className="card reveal">
        <div className="skeleton skeleton-title" style={{ width: '200px' }} />
        <div style={{ margin: '8px 0' }}>
          <span className="skeleton skeleton-text long" />
          <span className="skeleton skeleton-text long" style={{ marginTop: '4px' }} />
          <span className="skeleton skeleton-text medium" style={{ marginTop: '4px' }} />
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--space-sm)' }}>
        {[0, 1, 2].map((i) => (
          <div className="card reveal" key={i} style={{ borderLeft: '3px solid var(--color-rule-2)' }}>
            <div className="skeleton skeleton-title" style={{ width: '120px' }} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: 'var(--space-xs)' }}>
              {[0, 1, 2].map((j) => (
                <div key={j} style={{ padding: '8px 12px', background: 'var(--color-paper-3)', borderRadius: 'var(--radius-card)', height: '36px', display: 'flex', alignItems: 'center' }}>
                  <span className="skeleton skeleton-text long" />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="card reveal">
        <div className="skeleton skeleton-title" style={{ width: '140px' }} />
        <span className="skeleton skeleton-text long" />
      </div>
    </div>
  )
}

function HistoryPageSkeleton() {
  return (
    <div className="card reveal" style={{ marginTop: 'var(--space-md)' }}>
      <div className="card-header">
        <div>
          <div className="skeleton skeleton-title" style={{ width: '220px' }} />
          <div className="skeleton skeleton-text medium" style={{ width: '300px' }} />
        </div>
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th><span className="skeleton skeleton-text short" /></th>
            <th><span className="skeleton skeleton-text short" /></th>
            <th><span className="skeleton skeleton-text short" /></th>
            <th><span className="skeleton skeleton-text short" /></th>
            <th><span className="skeleton skeleton-text short" /></th>
          </tr>
        </thead>
        <tbody>
          {[0, 1, 2, 3, 4].map((i) => (
            <tr key={i}>
              <td><span className="skeleton skeleton-text medium" /></td>
              <td><span className="skeleton skeleton-text long" /></td>
              <td><span className="skeleton skeleton-text short" /></td>
              <td><span className="skeleton skeleton-text short" /></td>
              <td><span className="skeleton skeleton-text medium" /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── Dashboard Page (Bento Grid) ─────────────────────────────
function DashboardPage() {
  const [metrics, setMetrics] = useState<any>(null)
  const [health, setHealth] = useState<any>(null)
  const [alerts, setAlerts] = useState<any[]>([])
  const [timeline, setTimeline] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getDashboard(), getHealth(), getAlerts(), getTimeline()])
      .then(([d, h, a, t]) => {
        setMetrics(d.data.metrics)
        setHealth(h.data)
        setAlerts(a.data)
        setTimeline(t.data)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <DashboardPageSkeleton />

  const score = health?.health_score ?? 0
  const radius = 44; const circ = 2 * Math.PI * radius
  const offset = circ - (score / 100) * circ
  const ringColor = score >= 75 ? 'var(--color-success)' : score >= 50 ? 'var(--color-warning)' : 'var(--color-error)'

  return (
    <div className="page-body">
      <div className="bento-grid">
        {/* Row 1: KPI Metrics */}
        <div className="col-3 metric-tile reveal" style={{ '--i': 0, '--tile-accent': 'var(--color-success)', '--tile-icon-bg': 'oklch(68% 0.16 145 / 0.08)' } as any}>
          <div className="metric-tile-header">
            <span className="metric-label">Total Revenue</span>
            <div className="metric-icon"><DollarSign size={14} style={{ color: 'var(--color-success)' }} /></div>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
            <div className="metric-value">
              <NumberTicker value={metrics?.total_revenue ?? 0} formatFn={fmt} />
            </div>
            <Sparkline data={[12000, 15000, 18200, 16400, 21800, 24100, metrics?.total_revenue ?? 28000]} color="var(--color-success)" />
          </div>
        </div>

        <div className="col-3 metric-tile reveal" style={{ '--i': 1, '--tile-accent': 'var(--color-accent)', '--tile-icon-bg': 'oklch(60% 0.18 250 / 0.08)' } as any}>
          <div className="metric-tile-header">
            <span className="metric-label">Net Working Capital</span>
            <div className="metric-icon"><Activity size={14} style={{ color: 'var(--color-accent)' }} /></div>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
            <div className="metric-value">
              <NumberTicker value={metrics?.net_working_capital ?? 0} formatFn={fmt} />
            </div>
            <Sparkline data={[15000, 16100, 15300, 16900, 16100, metrics?.net_working_capital ?? 18000]} color="var(--color-accent)" />
          </div>
        </div>

        <div className="col-3 metric-tile reveal" style={{ '--i': 2, '--tile-accent': 'var(--color-info)', '--tile-icon-bg': 'oklch(66% 0.16 195 / 0.08)' } as any}>
          <div className="metric-tile-header">
            <span className="metric-label">Receivables (AR)</span>
            <div className="metric-icon"><ArrowUpRight size={14} style={{ color: 'var(--color-info)' }} /></div>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
            <div className="metric-value">
              <NumberTicker value={metrics?.accounts_receivable ?? 0} formatFn={fmt} />
            </div>
            <Sparkline data={[8200, 11400, 10200, 12600, 9700, metrics?.accounts_receivable ?? 11000]} color="var(--color-info)" />
          </div>
        </div>

        <div className="col-3 metric-tile reveal" style={{ '--i': 3, '--tile-accent': 'var(--color-warning)', '--tile-icon-bg': 'oklch(72% 0.15 75 / 0.08)' } as any}>
          <div className="metric-tile-header">
            <span className="metric-label">Active Customers</span>
            <div className="metric-icon"><Users size={14} style={{ color: 'var(--color-warning)' }} /></div>
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
            <div className="metric-value">
              <NumberTicker value={metrics?.active_customers ?? 0} />
            </div>
            <Sparkline data={[24, 26, 26, 29, 31, metrics?.active_customers ?? 34]} color="var(--color-warning)" />
          </div>
        </div>

        {/* Row 2: Business Health Console (Left) & Active Alerts (Right) */}
        <div className="col-6 row-2 card reveal" style={{ '--i': 4 } as any}>
          <div className="card-header">
            <div>
              <div className="card-title">Business Health telemetry</div>
              <div className="card-subtitle">Composite operational score matrix</div>
            </div>
            <span className="badge" style={{
              background: score >= 75 ? 'oklch(68% 0.16 145 / 0.08)' : score >= 50 ? 'oklch(72% 0.15 75 / 0.08)' : 'oklch(62% 0.18 25 / 0.08)',
              color: ringColor,
              borderColor: ringColor
            }}>{health?.status}</span>
          </div>

          <div className="health-ring-wrap" style={{ margin: 'var(--space-xs) 0' }}>
            <div className="health-ring">
              <svg width="96" height="96" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r={radius} fill="none" stroke="var(--color-rule-2)" strokeWidth="6" />
                <circle cx="50" cy="50" r={radius} fill="none" stroke={ringColor} strokeWidth="6"
                  strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
                  style={{ transition: 'stroke-dashoffset 1.2s cubic-bezier(0.16, 1, 0.3, 1)' }} />
              </svg>
              <div className="health-ring-label">
                <span className="health-ring-num" style={{ color: ringColor }}>
                  <NumberTicker value={score} />
                </span>
                <span className="health-ring-txt">/100</span>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2xs)', flex: 1 }}>
              {[
                { label: 'Gross Margin', value: `${health?.gross_profit_margin_pct?.toFixed(1)}%` },
                { label: 'Operating Ratio', value: health?.operating_ratio?.toFixed(3) },
                { label: 'Overdue Invoices', value: health?.overdue_invoices },
                { label: 'Low Stock SKUs', value: health?.low_stock_products },
              ].map(r => (
                <div key={r.label} style={{ display: 'flex', justifySelf: 'stretch', justifyContent: 'space-between', fontSize: 'var(--text-xs)', borderBottom: '1px solid var(--color-rule-2)', paddingBottom: '4px' }}>
                  <span style={{ color: 'var(--color-ink-2)' }}>{r.label}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--color-ink)' }}>{r.value ?? 0}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="col-6 row-2 card reveal" style={{ '--i': 5 } as any}>
          <div className="card-header">
            <div>
              <div className="card-title">Active Security & Risk Alerts</div>
              <div className="card-subtitle">{alerts.length} operational issues flag telemetry</div>
            </div>
          </div>
          {alerts.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon" style={{ color: 'var(--color-success)' }}><CheckCircle2 size={32} /></div>
              <h3>System Secured</h3>
              <p>No anomalous event vectors or risk actions flagged.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2xs)', maxHeight: '280px', overflowY: 'auto', paddingRight: '4px' }}>
              {alerts.map((a, i) => (
                <div className="alert-item" key={i}>
                  <span className={`alert-badge ${a.severity?.toLowerCase() === 'critical' ? 'critical' : 'warning'}`}>{a.severity}</span>
                  <div className="alert-body">
                    <div className="alert-title">{a.title || a.category}</div>
                    <div className="alert-msg">{a.message}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Row 3: Business Timeline (Left) & Secondary Metrics Grid (Right) */}
        <div className="col-8 card reveal" style={{ '--i': 6 } as any}>
          <div className="card-header">
            <div>
              <div className="card-title">System Event Log</div>
              <div className="card-subtitle">Real-time business operation audit timeline</div>
            </div>
          </div>
          {timeline.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon"><FileText size={32} /></div>
              <h3>Log Clear</h3>
              <p>Telemetry ledger is empty. Awaiting database transactions.</p>
            </div>
          ) : (
            <div className="timeline" style={{ maxHeight: '240px', overflowY: 'auto', paddingRight: '4px' }}>
              {timeline.slice(0, 10).map((ev, i) => (
                <div className="timeline-item" key={i}>
                  <div className="timeline-dot" style={{
                    background: ev.severity === 'CRITICAL' ? 'var(--color-error)' : ev.severity === 'WARNING' ? 'var(--color-warning)' : 'var(--color-accent)'
                  }} />
                  <div className="timeline-content">
                    <div className="timeline-event" style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>{ev.event_type}</span>
                      <span className="timeline-time">{new Date(ev.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <div className="timeline-desc">{ev.description}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="col-4 card reveal" style={{ '--i': 7 } as any}>
          <div className="card-header">
            <div>
              <div className="card-title">Secondary telemetry</div>
              <div className="card-subtitle">Ancillary business variables</div>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-2xs)', height: '100%' }}>
            {[
              { label: 'Payables (AP)', value: metrics?.accounts_payable ?? 0, format: fmt, color: 'var(--color-error)' },
              { label: 'Monthly Revenue', value: metrics?.monthly_revenue ?? 0, format: fmt, color: 'var(--color-success)' },
              { label: 'Low Stock SKUs', value: metrics?.low_stock_alerts ?? 0, format: (v: number) => String(v), color: metrics?.low_stock_alerts > 0 ? 'var(--color-error)' : 'var(--color-ink-2)' },
              { label: 'Monthly Orders', value: metrics?.monthly_orders ?? 0, format: (v: number) => String(v), color: 'var(--color-accent)' },
            ].map(item => (
              <div key={item.label} style={{ background: 'var(--color-paper-3)', padding: 'var(--space-2xs)', borderRadius: 'var(--radius-card)', border: '1px solid var(--color-rule-2)' }}>
                <div style={{ fontSize: '0.62rem', fontFamily: 'var(--font-mono)', color: 'var(--color-muted)', textTransform: 'uppercase', marginBottom: '2px' }}>{item.label}</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-md)', fontWeight: 600, color: item.color }}>
                  <NumberTicker value={item.value} formatFn={item.format} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Forecast Page (Workbench Structure with SVG Chart) ──────
function ForecastPage() {
  const [revenue, setRevenue] = useState<any>(null)
  const [cashflow, setCashflow] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getRevenueForecast(), getCashflowForecast()])
      .then(([r, c]) => { setRevenue(r.data); setCashflow(c.data) })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <ForecastPageSkeleton />

  return (
    <div className="page-body">
      <div className="bento-grid">
        {/* Left Column: Revenue Projection Workbench */}
        <div className="col-6 card reveal" style={{ '--i': 0 } as any}>
          <div className="card-header">
            <div>
              <div className="card-title">90-Day Revenue Forecasting Model</div>
              <div className="card-subtitle">Statistical model based on historical aggregates</div>
            </div>
            <span className="badge blue">Confidence: {pct(revenue?.confidence_score ?? 0)}</span>
          </div>

          <div style={{ margin: 'var(--space-3xs) 0' }}>
            <div className="forecast-value" style={{ color: 'var(--color-success)' }}>
              {revenue?.metadata?.forecasted_value ? (
                <NumberTicker value={revenue.metadata.forecasted_value} formatFn={fmt} />
              ) : '—'}
            </div>
            <div className="forecast-label">Projected gross incoming transactions (90d)</div>
          </div>

          <div className="confidence-bar">
            <div className="confidence-fill" style={{ width: `${(revenue?.confidence_score ?? 0) * 100}%` }} />
          </div>

          <div style={{ display: 'flex', justifySelf: 'stretch', justifyContent: 'space-between', fontSize: '0.68rem', fontFamily: 'var(--font-mono)', color: 'var(--color-muted)', borderBottom: '1px solid var(--color-rule-2)', paddingBottom: '4px' }}>
            <span>DATA SAMPLE MATRIX</span>
            <span>{revenue?.metadata?.data_points ?? 0} NODES DETECTED</span>
          </div>

          {revenue?.metadata?.forecasted_value && (
            <TelemetryChart baseValue={revenue.metadata.forecasted_value} confidence={revenue?.confidence_score ?? 0} color="var(--color-success)" secondaryColor="var(--color-success-dim)" days={90} />
          )}

          <div style={{ padding: 'var(--space-xs)', background: 'var(--color-paper-3)', borderLeft: '3px solid var(--color-accent)', borderRadius: 'var(--radius-card)', fontSize: 'var(--text-xs)', color: 'var(--color-ink-2)', lineHeight: 1.5, marginTop: 'var(--space-2xs)' }}>
            <div style={{ fontWeight: 600, color: 'var(--color-ink)', marginBottom: '4px', fontFamily: 'var(--font-display)' }}>Decision Suggestion:</div>
            {revenue?.suggested_action}
          </div>
        </div>

        {/* Right Column: Cash Flow Telemetry */}
        <div className="col-6 card reveal" style={{ '--i': 1 } as any}>
          <div className="card-header">
            <div>
              <div className="card-title">30-Day Liquidity & Cash Flow Forecast</div>
              <div className="card-subtitle">Deterministic short-term capital ledger</div>
            </div>
            <span className={`badge ${cashflow?.metadata?.net_balance >= 0 ? 'green' : 'red'}`}>
              Risk: {cashflow?.metadata?.risk_level ?? 'UNKNOWN'}
            </span>
          </div>

          <div style={{ margin: 'var(--space-3xs) 0' }}>
            <div className="forecast-value" style={{ color: cashflow?.metadata?.net_balance >= 0 ? 'var(--color-success)' : 'var(--color-error)' }}>
              {cashflow?.metadata?.net_balance !== undefined ? (
                <NumberTicker value={cashflow.metadata.net_balance} formatFn={fmt} />
              ) : '—'}
            </div>
            <div className="forecast-label">Net Balance Position (30d)</div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-2xs)', marginTop: 'var(--space-2xs)' }}>
            {[
              { label: 'Receivables (AR)', value: cashflow?.metadata?.total_ar ?? 0, color: 'var(--color-success)' },
              { label: 'Payables (AP)', value: cashflow?.metadata?.total_ap ?? 0, color: 'var(--color-error)' },
              { label: 'Liquidity Ratio', value: cashflow?.metadata?.liquidity_ratio ?? 0, color: 'var(--color-accent)' },
              { label: 'Cash Health Level', value: cashflow?.metadata?.risk_level ?? '—', color: 'var(--color-warning)' },
            ].map(r => (
              <div key={r.label} style={{ background: 'var(--color-paper-3)', borderRadius: 'var(--radius-card)', padding: 'var(--space-2xs) var(--space-xs)', border: '1px solid var(--color-rule-2)' }}>
                <div style={{ fontSize: '0.62rem', fontFamily: 'var(--font-mono)', color: 'var(--color-muted)', textTransform: 'uppercase', marginBottom: '2px' }}>{r.label}</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-sm)', fontWeight: 700, color: r.color }}>
                  {typeof r.value === 'number' ? (
                    <NumberTicker value={r.value} formatFn={r.label.includes('Ratio') ? (v) => v.toFixed(2) : fmt} />
                  ) : r.value}
                </div>
              </div>
            ))}
          </div>

          {cashflow?.metadata?.net_balance !== undefined && (
            <TelemetryChart baseValue={Math.abs(cashflow.metadata.net_balance)} confidence={0.82} color="var(--color-accent)" secondaryColor="var(--color-accent-dim)" days={30} />
          )}
        </div>

        {/* Section 2: Executive Impact Matrices */}
        <div className="col-12 card reveal" style={{ '--i': 2 } as any}>
          <div className="card-header">
            <div>
              <div className="card-title">Strategic Insights & Decision Matrix</div>
              <div className="card-subtitle">AI synthesis of forecasted outcomes</div>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-sm)' }}>
            {[
              { title: 'Revenue Vector Impact', data: revenue, border: 'var(--color-success)' },
              { title: 'Liquidity Ledger Impact', data: cashflow, border: 'var(--color-info)' }
            ].map((f, i) => (
              <div key={i} style={{ padding: 'var(--space-sm)', background: 'var(--color-paper-3)', borderRadius: 'var(--radius-card)', border: '1px solid var(--color-rule)', borderLeft: `4px solid ${f.border}` }}>
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--color-ink)', marginBottom: 'var(--space-2xs)', fontFamily: 'var(--font-display)' }}>{f.title}</div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-2)', lineHeight: 1.6, marginBottom: 'var(--space-2xs)' }}>{f.data?.business_impact}</div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-accent)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>→ {f.data?.suggested_action}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Materials Page (Raw Materials & Pricing Engine) ──────────
function MaterialsPage() {
  const [materials, setMaterials] = useState<any[]>([])
  const [products, setProducts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState<number | null>(null)
  
  const [form, setForm] = useState({
    name: '',
    unit: '',
    current_unit_price: '',
    supplier_id: '',
    reorder_threshold: '',
    product_ids: [] as number[],
  })
  
  const [forecastProduct, setForecastProduct] = useState('')
  const [forecastLoading, setForecastLoading] = useState(false)
  const [forecastResult, setForecastResult] = useState<any>(null)
  const [histories, setHistories] = useState<Record<number, any[]>>({})
  const [buyingAdvice, setBuyingAdvice] = useState<any[]>([])

  const loadData = useCallback(() => {
    setLoading(true)
    Promise.all([getMaterials(), getProducts(), getMaterialBuyingAdvice()])
      .then(async ([mRes, pRes, aRes]) => {
        const mats = mRes.data
        setMaterials(mats)
        setProducts(pRes.data)
        setBuyingAdvice(aRes.data)
        
        const histMap: Record<number, any[]> = {}
        for (const m of mats) {
          try {
            const hRes = await getMaterialPriceHistory(m.id)
            histMap[m.id] = hRes.data
          } catch (e) {
            console.error(e)
          }
        }
        setHistories(histMap)
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name || !form.unit) return
    const payload = {
      name: form.name,
      unit: form.unit,
      current_unit_price: parseFloat(form.current_unit_price) || 0.0,
      supplier_id: form.supplier_id ? parseInt(form.supplier_id) : null,
      reorder_threshold: parseFloat(form.reorder_threshold) || 0.0,
      product_ids: form.product_ids
    }
    
    try {
      if (editingId) {
        await updateMaterial(editingId, payload)
      } else {
        await createMaterial(payload)
      }
      setForm({ name: '', unit: '', current_unit_price: '', supplier_id: '', reorder_threshold: '', product_ids: [] })
      setEditingId(null)
      loadData()
    } catch (err) {
      console.error(err)
    }
  }

  const handleEdit = (m: any) => {
    setEditingId(m.id)
    setForm({
      name: m.name,
      unit: m.unit,
      current_unit_price: String(m.current_unit_price),
      supplier_id: m.supplier_id ? String(m.supplier_id) : '',
      reorder_threshold: String(m.reorder_threshold),
      product_ids: m.product_ids || []
    })
  }

  const handleDelete = async (id: number) => {
    if (!window.confirm('Delete this material?')) return
    try {
      await deleteMaterial(id)
      loadData()
    } catch (err) {
      console.error(err)
    }
  }

  const handleForecast = async () => {
    if (!forecastProduct) return
    setForecastLoading(true)
    try {
      const res = await getMaterialForecast(parseInt(forecastProduct))
      setForecastResult(res.data)
    } catch (err) {
      console.error(err)
    } finally {
      setForecastLoading(false)
    }
  }

  const handleAddPriceHistory = async (materialId: number, currentPrice: number) => {
    const newPriceStr = window.prompt(`Log new price for this material (Current: $${currentPrice}):`, String(currentPrice))
    if (!newPriceStr) return
    const newPrice = parseFloat(newPriceStr)
    if (isNaN(newPrice) || newPrice < 0) {
      alert('Invalid price value')
      return
    }
    try {
      await createPriceHistory({
        material_id: materialId,
        recorded_price: newPrice,
        source: 'MANUAL'
      })
      loadData()
    } catch (err) {
      console.error(err)
    }
  }

  if (loading) {
    return <div className="page-body"><div className="card reveal"><div className="empty-state">Loading materials engine...</div></div></div>
  }

  return (
    <div className="page-body">
      <div className="bento-grid">
        {/* Left column: Raw Materials list & Add Form */}
        <div className="col-7 card reveal" style={{ '--i': 0 } as any}>
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div className="card-title">Raw Material Stock Ledger</div>
              <div className="card-subtitle">Track raw resources, spot pricing, and product allocations</div>
            </div>
          </div>
          
          {materials.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon"><Activity size={32} /></div>
              <h3>No Materials Logged</h3>
              <p>Initialize raw material records below to track spot price fluctuations.</p>
            </div>
          ) : (
            <table className="data-table" style={{ width: '100%' }}>
              <thead>
                <tr>
                  <th>Material</th>
                  <th>Spot Price</th>
                  <th>Trend (90d)</th>
                  <th>Reorder Point</th>
                  <th>Linked Products</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {materials.map(m => {
                  const histList = histories[m.id] || []
                  const prices = histList.map((h: any) => h.recorded_price).reverse()
                  if (prices.length === 0 || prices[prices.length - 1] !== m.current_unit_price) {
                    prices.push(m.current_unit_price)
                  }
                  
                  return (
                    <tr key={m.id}>
                      <td>
                        <strong>{m.name}</strong>
                        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-2)' }}>Unit: {m.unit}</div>
                      </td>
                      <td>
                        <span style={{ fontFamily: 'var(--font-mono)' }}>${m.current_unit_price.toFixed(2)}</span>
                      </td>
                      <td>
                        {prices.length > 1 ? (
                          <Sparkline data={prices} color="var(--color-success)" />
                        ) : (
                          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted)' }}>Stable</span>
                        )}
                      </td>
                      <td>{m.reorder_threshold} {m.unit}</td>
                      <td>
                        <span className="badge info">{m.product_ids?.length || 0} Products</span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button className="badge amber" style={{ border: 'none', cursor: 'pointer' }} onClick={() => handleEdit(m)}>Edit</button>
                          <button className="badge green" style={{ border: 'none', cursor: 'pointer' }} onClick={() => handleAddPriceHistory(m.id, m.current_unit_price)}>+ Price</button>
                          <button className="badge red" style={{ border: 'none', cursor: 'pointer' }} onClick={() => handleDelete(m.id)}>Delete</button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}

          {/* Form */}
          <div style={{ borderTop: '1px solid var(--color-rule-2)', marginTop: '20px', paddingTop: '20px' }}>
            <h3 style={{ marginBottom: '15px' }}>{editingId ? 'Edit Raw Material' : 'Log New Raw Material'}</h3>
            <form onSubmit={handleSave}>
              <div className="form-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
                <div className="form-group">
                  <label className="form-label">Material Name</label>
                  <input className="form-input" type="text" placeholder="e.g., Steel Sheet" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Measurement Unit</label>
                  <input className="form-input" type="text" placeholder="e.g., kg, unit, liter" value={form.unit} onChange={e => setForm({ ...form, unit: e.target.value })} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Current Spot Price ($)</label>
                  <input className="form-input" type="number" step="0.01" placeholder="0.00" value={form.current_unit_price} onChange={e => setForm({ ...form, current_unit_price: e.target.value })} />
                </div>
                <div className="form-group">
                  <label className="form-label">Reorder Threshold</label>
                  <input className="form-input" type="number" step="0.1" placeholder="e.g., 50" value={form.reorder_threshold} onChange={e => setForm({ ...form, reorder_threshold: e.target.value })} />
                </div>
                <div className="form-group" style={{ gridColumn: 'span 2' }}>
                  <label className="form-label">Associate with Product Catalog SKUs</label>
                  <select 
                    multiple 
                    className="form-input" 
                    style={{ height: '100px', background: 'var(--color-paper-3)' }} 
                    value={form.product_ids.map(String)} 
                    onChange={e => {
                      const selected = Array.from(e.target.selectedOptions, option => parseInt(option.value))
                      setForm({ ...form, product_ids: selected })
                    }}
                  >
                    {products.map(p => (
                      <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>
                    ))}
                  </select>
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-2)' }}>Hold Ctrl (Cmd) to select multiple products.</span>
                </div>
              </div>
              <div style={{ marginTop: '15px', display: 'flex', gap: '10px' }}>
                <button type="submit" className="theme-toggle" style={{ background: 'var(--color-accent)', color: 'var(--color-accent-ink)', padding: '8px 16px', borderRadius: 'var(--radius-button)', border: 'none', cursor: 'pointer' }}>
                  {editingId ? 'Apply Update' : 'Register Material'}
                </button>
                {editingId && (
                  <button type="button" className="theme-toggle" style={{ padding: '8px 16px', borderRadius: 'var(--radius-button)', border: 'none', cursor: 'pointer' }} onClick={() => {
                    setEditingId(null)
                    setForm({ name: '', unit: '', current_unit_price: '', supplier_id: '', reorder_threshold: '', product_ids: [] })
                  }}>
                    Cancel
                  </button>
                )}
              </div>
            </form>
          </div>
        </div>

        {/* Right column: Margin Forecast Simulator */}
        <div className="col-5 card reveal" style={{ '--i': 1 } as any}>
          <div className="card-header">
            <div>
              <div className="card-title">Material-Linked Margin Forecast</div>
              <div className="card-subtitle">Project product profit margins derived from raw material price shifts</div>
            </div>
          </div>
          
          <div className="form-group" style={{ marginBottom: '20px' }}>
            <label className="form-label">Select Product to Run Projection</label>
            <select className="form-input" style={{ background: 'var(--color-paper-3)' }} value={forecastProduct} onChange={e => setForecastProduct(e.target.value)}>
              <option value="">-- Choose Product --</option>
              {products.map(p => (
                <option key={p.id} value={p.id}>{p.name} (Price: ${p.price.toFixed(2)})</option>
              ))}
            </select>
          </div>
          
          <button 
            className="theme-toggle" 
            style={{ width: '100%', padding: '12px', background: 'var(--color-accent)', color: 'var(--color-accent-ink)', borderRadius: 'var(--radius-button)', border: 'none', cursor: 'pointer' }} 
            onClick={handleForecast}
            disabled={!forecastProduct || forecastLoading}
          >
            {forecastLoading ? 'Calculating Margins...' : 'Run Margin Forecast'}
          </button>
          
          {forecastResult && (
            <div style={{ marginTop: '25px', padding: '15px', border: '1px solid var(--color-rule)', borderRadius: 'var(--radius-card)', background: 'var(--color-paper-2)' }}>
              <h4 style={{ marginBottom: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sparkles size={16} /> Margins Projection Results
              </h4>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px dashed var(--color-rule-2)', paddingBottom: '6px' }}>
                  <span style={{ color: 'var(--color-ink-2)' }}>Product SKU:</span>
                  <strong>{forecastResult.sku}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px dashed var(--color-rule-2)', paddingBottom: '6px' }}>
                  <span style={{ color: 'var(--color-ink-2)' }}>Selling Price:</span>
                  <strong>${forecastResult.price.toFixed(2)}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px dashed var(--color-rule-2)', paddingBottom: '6px' }}>
                  <span style={{ color: 'var(--color-ink-2)' }}>Original COGS:</span>
                  <strong>${forecastResult.original_cogs.toFixed(2)}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px dashed var(--color-rule-2)', paddingBottom: '6px' }}>
                  <span style={{ color: 'var(--color-ink-2)' }}>Projected COGS:</span>
                  <strong style={{ color: forecastResult.projected_cogs > forecastResult.original_cogs ? 'var(--color-error)' : 'var(--color-success)' }}>
                    ${forecastResult.projected_cogs.toFixed(2)}
                  </strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px dashed var(--color-rule-2)', paddingBottom: '6px' }}>
                  <span style={{ color: 'var(--color-ink-2)' }}>Original Gross Margin:</span>
                  <strong>{(forecastResult.original_margin * 100).toFixed(1)}%</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px' }}>
                  <span style={{ color: 'var(--color-ink-2)' }}>Projected Gross Margin:</span>
                  <strong style={{ fontSize: 'var(--text-md)', color: forecastResult.projected_margin < forecastResult.original_margin ? 'var(--color-error)' : 'var(--color-success)' }}>
                    {(forecastResult.projected_margin * 100).toFixed(1)}%
                  </strong>
                </div>
              </div>
              
              {forecastResult.projected_margin < forecastResult.original_margin && (
                <div className="alert-banner warning" style={{ marginTop: '15px', padding: '10px', fontSize: 'var(--text-xs)' }}>
                  ⚠ Margin erosion detected! Raw materials spot prices exceed the current product production cost. Consider raising product selling price or renegotiating with suppliers.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Strategic Procurement Buying Advice */}
        <div className="col-12 card reveal" style={{ '--i': 2, marginTop: '20px' } as any}>
          <div className="card-header">
            <div>
              <div className="card-title">Strategic Procurement Timing &amp; Stockpile Advice</div>
              <div className="card-subtitle">Automated pricing trends and seasonal patterns analyzed from log records</div>
            </div>
          </div>
          <div style={{ padding: '20px' }}>
            {buyingAdvice.length === 0 ? (
              <div className="empty-state">
                <p>Register materials and log historical price data points to generate purchasing timing advices.</p>
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Material</th>
                    <th>Current Spot Price</th>
                    <th>Historical Average</th>
                    <th>Best Month to Buy</th>
                    <th>Purchasing Timing Advice</th>
                    <th>AI Trend Justification</th>
                  </tr>
                </thead>
                <tbody>
                  {buyingAdvice.map((adv, idx) => {
                    const badgeClass = adv.advice === 'STOCKPILE' ? 'green' : adv.advice === 'DELAY' ? 'red' : adv.advice === 'HOLD' ? 'amber' : 'gray'
                    return (
                      <tr key={idx}>
                        <td style={{ fontWeight: 600, color: 'var(--color-ink)' }}>{adv.name}</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>${adv.current_unit_price.toFixed(2)}</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>${adv.historical_average.toFixed(2)}</td>
                        <td style={{ fontWeight: 600, color: 'var(--color-accent)' }}>{adv.best_month_to_buy}</td>
                        <td>
                          <span className={`badge ${badgeClass}`}>{adv.advice}</span>
                        </td>
                        <td style={{ fontSize: '0.72rem', color: 'var(--color-ink-2)', maxWidth: '400px' }}>{adv.justification}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Risk Page (Tabular Console) ──────────────────────────────
function RiskPage() {
  const [customers, setCustomers] = useState<any[]>([])
  const [suppliers, setSuppliers] = useState<any[]>([])
  const [pricing, setPricing] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<'churn' | 'collections'>('churn')
  const [filterBy, setFilterBy] = useState<'all' | 'high_collections'>('all')

  useEffect(() => {
    Promise.all([getCustomerRisk(), getSupplierRisk(), getPricing()])
      .then(([c, s, p]) => { setCustomers(c.data); setSuppliers(s.data); setPricing(p.data) })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <RiskPageSkeleton />

  const riskBadge = (r: string) => {
    const norm = r?.toUpperCase()
    const label = norm === 'CRITICAL' || norm === 'HIGH' ? 'red' : norm === 'MEDIUM' || norm === 'AMBER' ? 'amber' : 'green'
    return <span className={`badge ${label}`}>{r}</span>
  }

  const processedCustomers = customers
    .filter(c => {
      if (filterBy === 'high_collections') {
        return (c.collections_risk_score ?? 0) > 70
      }
      return true
    })
    .sort((a, b) => {
      if (sortBy === 'collections') {
        return (b.collections_risk_score ?? 0) - (a.collections_risk_score ?? 0)
      }
      return (b.churn_probability ?? 0) - (a.churn_probability ?? 0)
    })

  return (
    <div className="page-body">
      {/* Customer Risk Registry */}
      <div className="card reveal" style={{ '--i': 0 } as any}>
        <div className="card-header" style={{ flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div className="card-title">Customer Portfolio Risk Telemetry</div>
            <div className="card-subtitle">{processedCustomers.length} ledger instances analyzed</div>
          </div>
          <div style={{ display: 'flex', gap: '12px', marginLeft: 'auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--color-muted)' }}>Sort:</span>
              <select 
                value={sortBy} 
                onChange={(e) => setSortBy(e.target.value as any)}
                style={{ background: 'var(--color-paper-2)', color: 'var(--color-ink)', border: '1px solid var(--color-rule)', borderRadius: '4px', padding: '4px 8px', fontSize: '0.75rem' }}
              >
                <option value="churn">Churn Risk Index</option>
                <option value="collections">Collections Risk</option>
              </select>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--color-muted)' }}>Filter:</span>
              <select 
                value={filterBy} 
                onChange={(e) => setFilterBy(e.target.value as any)}
                style={{ background: 'var(--color-paper-2)', color: 'var(--color-ink)', border: '1px solid var(--color-rule)', borderRadius: '4px', padding: '4px 8px', fontSize: '0.75rem' }}
              >
                <option value="all">Show All</option>
                <option value="high_collections">High Collections Risk (&gt;70)</option>
              </select>
            </div>
          </div>
        </div>
        {processedCustomers.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon"><Users size={32} /></div>
            <h3>No Customer Nodes</h3>
            <p>No customer records match the current filter selection.</p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Customer Node</th>
                <th>Churn Risk Index</th>
                <th>Receivables Risk</th>
                <th>Collections Risk</th>
                <th>Lifetime Capital (CLV)</th>
                <th>Automated Action Recommendation</th>
              </tr>
            </thead>
            <tbody>
              {processedCustomers.map((c, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600, color: 'var(--color-ink)' }}>{c.name}</td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>
                    {riskBadge(c.churn_probability > 0.5 ? 'HIGH' : c.churn_probability > 0.25 ? 'MEDIUM' : 'LOW')}
                    <span style={{ marginLeft: '8px', color: 'var(--color-muted)' }}>{pct(c.churn_probability)}</span>
                  </td>
                  <td>{riskBadge(c.late_payment_risk)}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                    {c.collections_risk_score !== undefined ? (
                      <span style={{ color: c.collections_risk_score > 70 ? 'var(--color-error)' : c.collections_risk_score > 40 ? 'var(--color-warning)' : 'var(--color-success)' }}>
                        {c.collections_risk_score.toFixed(0)}/100
                      </span>
                    ) : '—'}
                  </td>
                  <td style={{ color: 'var(--color-success)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{fmt(c.clv ?? 0)}</td>
                  <td style={{ fontSize: '0.72rem', color: 'var(--color-ink-2)', maxWidth: '300px' }}>{c.suggested_action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Supplier Reliability Registry */}
      <div className="card reveal" style={{ '--i': 1 } as any}>
        <div className="card-header">
          <div>
            <div className="card-title">Supplier Vector Risk Registry</div>
            <div className="card-subtitle">{suppliers.length} node pipelines monitored</div>
          </div>
        </div>
        {suppliers.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon"><Truck size={32} /></div>
            <h3>No Supplier Nodes</h3>
            <p>Pipelines empty. Register suppliers to initiate monitoring.</p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Supplier Node</th>
                <th>Delivery Risk Index</th>
                <th>Telemetry Reliability</th>
                <th>Mean Lead Duration</th>
                <th>Market Price Risk</th>
                <th>Payment Delay (Avg)</th>
                <th>Margin Erosion</th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map((s, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600, color: 'var(--color-ink)' }}>{s.name}</td>
                  <td>{riskBadge(s.delay_risk)}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ flex: 1, height: '4px', background: 'var(--color-rule-2)', borderRadius: '99px', overflow: 'hidden' }}>
                        <div style={{
                          width: `${s.reliability_score * 100}%`,
                          height: '100%',
                          background: s.reliability_score > 0.8 ? 'var(--color-success)' : s.reliability_score > 0.6 ? 'var(--color-warning)' : 'var(--color-error)'
                        }} />
                      </div>
                      <span style={{ fontSize: '0.68rem', fontFamily: 'var(--font-mono)', width: '32px' }}>{pct(s.reliability_score)}</span>
                    </div>
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>{s.metadata?.average_lead_days ?? '—'} days</td>
                  <td>{riskBadge(s.metadata?.price_risk ?? 'LOW')}</td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>{s.metadata?.invoice_delay ? `${s.metadata.invoice_delay} days` : '0 days'}</td>
                  <td>{s.metadata?.margin_erosion_count ? <span className="badge red">{s.metadata.margin_erosion_count} Shipments</span> : <span className="badge green">None</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Product Pricing Matrix */}
      <div className="card reveal" style={{ '--i': 2 } as any}>
        <div className="card-header">
          <div>
            <div className="card-title">Product Pricing & Profit Optimization Ledger</div>
            <div className="card-subtitle">{pricing.length} optimized stock items</div>
          </div>
        </div>
        {pricing.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon"><MoneyIcon size={32} /></div>
            <h3>No Product Telemetry</h3>
            <p>Product database empty. Supply inventory coordinates.</p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Optimized Item</th>
                <th>SKU Hash</th>
                <th>Base Cost</th>
                <th>Optimized Target Price</th>
                <th>Profit / Unit Margin</th>
                <th>Est. Revenue Uplift (Annual)</th>
              </tr>
            </thead>
            <tbody>
              {pricing.map((p, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600, color: 'var(--color-ink)' }}>{p.name}</td>
                  <td><span className="badge blue">{p.sku}</span></td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>${p.current_price?.toFixed(2)}</td>
                  <td style={{ color: 'var(--color-success)', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>${p.recommended_price?.toFixed(2)}</td>
                  <td style={{ color: 'var(--color-info)', fontFamily: 'var(--font-mono)' }}>${p.expected_profit_per_unit?.toFixed(2)}</td>
                  <td style={{ color: 'var(--color-warning)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{fmt(p.expected_revenue_uplift ?? 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

// ─── Agents Page (Multi-Agent Engine) ──────────────────────────
function AgentsPage() {
  const [agents, setAgents] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [ran, setRan] = useState(false)

  const run = useCallback(async () => {
    setLoading(true)
    try { const r = await getAgents(); setAgents(r.data.agents ?? []); setRan(true) }
    finally { setLoading(false) }
  }, [])

  const riskColor = (r: string) => {
    const norm = r?.toUpperCase()
    return ({ CRITICAL: 'var(--color-error)', HIGH: 'var(--color-error)', MEDIUM: 'var(--color-warning)', LOW: 'var(--color-success)', UNKNOWN: 'var(--color-muted)' })[norm] ?? 'var(--color-muted)'
  }

  return (
    <div className="page-body">
      <div className="card reveal" style={{ '--i': 0 } as any}>
        <div className="card-header">
          <div>
            <div className="card-title">Multi-Agent Intelligence Network</div>
            <div className="card-subtitle">Parallel specialized LLM nodes orchestrated by CEO controller</div>
          </div>
          <button className="btn btn-primary" onClick={run} disabled={loading}>
            {loading ? <><div className="spinner" /> Synthesizing Nodes…</> : <><Play size={14} /> Execute Analysis Run</>}
          </button>
        </div>
        {!ran && !loading && (
          <div className="empty-state" style={{ padding: 'var(--space-xl) 0' }}>
            <div className="empty-icon" style={{ color: 'var(--color-accent)' }}><Bot size={40} /></div>
            <h3>Engine Idle</h3>
            <p>Awaiting trigger signal to invoke all 6 specialist agents. Each agent queries a distinct business subsystem matrix.</p>
          </div>
        )}
      </div>

      {loading && <AgentsPageSkeleton />}

      {ran && !loading && (
        <>
          {/* Operations Geographic Heatmap */}
          {agents.find(a => a.agent_name === 'OperationsAgent')?.geographic_sales_density && (
            <div className="card reveal" style={{ '--i': 1, marginBottom: '24px' } as any}>
              <div className="card-header">
                <div>
                  <div className="card-title">Geographic Sales Density & Staffing Optimizer</div>
                  <div className="card-subtitle">Real-time telemetry parsed from customer regional mapping data</div>
                </div>
              </div>
              <div style={{ padding: '20px' }}>
                <OperationsHeatmap data={agents.find(a => a.agent_name === 'OperationsAgent').geographic_sales_density} />
              </div>
            </div>
          )}

          <div className="agent-grid">
            {agents.map((a, idx) => {
              const meta = AGENT_META[a.agent_name] ?? { icon: '🤖', color: 'rgba(99,179,237,0.08)', border: 'var(--color-accent)' }
              const rc = riskColor(a.risk_level)
              return (
                <div className="agent-card reveal" key={idx} style={{ '--i': idx + 1 } as any}>
                  <div className="agent-header">
                    <div className="agent-avatar" style={{ '--agent-color': meta.color } as any}>{meta.icon}</div>
                    <div>
                      <div className="agent-name">{a.agent_name}</div>
                      <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
                        <span className="badge" style={{ background: `${rc}12`, color: rc, borderColor: `${rc}25` }}>{a.risk_level}</span>
                        <span className="badge blue">Confidence: {pct(a.confidence)}</span>
                      </div>
                    </div>
                  </div>
                  <div className="agent-analysis">{a.analysis}</div>
                  <div className="agent-recs">
                    {(a.recommendations ?? []).map((r: string, j: number) => (
                      <div className="agent-rec" key={j} style={{ '--agent-border': meta.border } as any}>
                        {r}
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

// ─── Simulate Page (Workbench Split Panel) ────────────────────
function SimulatePage() {
  const [form, setForm] = useState({
    price_changes: '', new_hires: '', avg_new_hire_salary: '50000',
    inventory_investment: '', loan_amount: '', loan_interest_rate_pct: '5',
    marketing_spend: '', supplier_change: '',
  })
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const run = async () => {
    setLoading(true)
    try {
      const payload: any = {}
      if (form.new_hires) payload.new_hires = parseInt(form.new_hires)
      if (form.avg_new_hire_salary) payload.avg_new_hire_salary = parseFloat(form.avg_new_hire_salary)
      if (form.inventory_investment) payload.inventory_investment = parseFloat(form.inventory_investment)
      if (form.loan_amount) payload.loan_amount = parseFloat(form.loan_amount)
      if (form.loan_interest_rate_pct) payload.loan_interest_rate_pct = parseFloat(form.loan_interest_rate_pct)
      if (form.marketing_spend) payload.marketing_spend = parseFloat(form.marketing_spend)
      if (form.supplier_change) payload.supplier_change = form.supplier_change
      const r = await simulate(payload)
      setResult(r.data)
    } finally { setLoading(false) }
  }

  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }))

  const healthColor = result?.business_health_score >= 70 ? 'var(--color-success)' : result?.business_health_score >= 40 ? 'var(--color-warning)' : 'var(--color-error)'

  return (
    <div className="page-body">
      <div className="bento-grid">
        {/* Left Side: Input Parameters Console */}
        <div className="col-5 card reveal" style={{ '--i': 0 } as any}>
          <div className="card-header">
            <div>
              <div className="card-title">Digital Twin Simulation Console</div>
              <div className="card-subtitle">Model hypothetical scenarios without mutating system database</div>
            </div>
          </div>

          <div className="form-grid" style={{ gridTemplateColumns: '1fr' }}>
            {[
              { label: 'New Hires Matrix Count', key: 'new_hires', placeholder: 'e.g. 3' },
              { label: 'Mean Salary Budget ($/yr)', key: 'avg_new_hire_salary', placeholder: '50000' },
              { label: 'Inventory Procurement ($)', key: 'inventory_investment', placeholder: 'e.g. 10000' },
              { label: 'Hypothetical Loan Credit ($)', key: 'loan_amount', placeholder: 'e.g. 50000' },
              { label: 'Annual Loan Interest Rate (%)', key: 'loan_interest_rate_pct', placeholder: '5' },
              { label: 'Monthly Marketing Budget ($)', key: 'marketing_spend', placeholder: 'e.g. 2000' },
            ].map(f => (
              <div className="form-group" key={f.key}>
                <label className="form-label">{f.label}</label>
                <input className="form-input" type="number" placeholder={f.placeholder}
                  value={(form as any)[f.key]} onChange={e => set(f.key, e.target.value)} />
              </div>
            ))}
            <div className="form-group">
              <label className="form-label">Supplier Consolidation Strategy</label>
              <select className="form-input" style={{ background: 'var(--color-paper-3)' }} value={form.supplier_change} onChange={e => set('supplier_change', e.target.value)}>
                <option value="">No change vector</option>
                <option value="diversify">Diversify provider channels</option>
                <option value="single_source">Consolidate single channel</option>
              </select>
            </div>
          </div>

          <div style={{ marginTop: 'var(--space-2xs)' }}>
            <button className="btn btn-primary" style={{ width: '100%' }} onClick={run} disabled={loading}>
              {loading ? <><div className="spinner" />Simulating Telemetry…</> : <><Activity size={14} /> Calculate Scenarios</>}
            </button>
          </div>
        </div>

        {/* Right Side: Projections Output Ledger */}
        <div className="col-7 card reveal" style={{ '--i': 1 } as any}>
          <div className="card-header">
            <div>
              <div className="card-title">Digital Twin Projections Telemetry</div>
              <div className="card-subtitle">Projected outputs for input scenario profile</div>
            </div>
            {result && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.68rem', color: 'var(--color-muted)', fontFamily: 'var(--font-mono)' }}>Health Score</span>
                <span style={{ fontSize: 'var(--text-lg)', fontWeight: 800, color: healthColor, fontFamily: 'var(--font-mono)' }}>{result.business_health_score}</span>
              </div>
            )}
          </div>

          {!result ? (
            <div className="empty-state" style={{ height: '100%', minHeight: '380px' }}>
              <div className="empty-icon"><Sliders size={36} /></div>
              <h3>Telemetry Engine Idle</h3>
              <p>Configure parameters on the left console panel and execute simulation run to render twin predictions.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-accent)' }}>
                SCENARIO PROFILE: {result.scenario_label}
              </div>

              <div className="sim-results-grid">
                {[
                  { l: 'Projected Gross Revenue', v: result.projected_revenue, c: 'var(--color-success)' },
                  { l: 'Projected Net Margin', v: result.projected_profit, c: result.projected_profit >= 0 ? 'var(--color-success)' : 'var(--color-error)' },
                  { l: 'Projected Net Cash Flow', v: result.projected_cash_flow, c: 'var(--color-info)' },
                  { l: 'Aggregate Risk Variable', v: result.risk_score, c: result.risk_score > 0.5 ? 'var(--color-error)' : 'var(--color-success)' },
                  { l: 'Inventory Pipeline Health', v: result.inventory_health, c: result.inventory_health === 'HEALTHY' ? 'var(--color-success)' : 'var(--color-warning)' },
                  { l: 'Synthetic Health Index', v: result.business_health_score, c: healthColor },
                ].map(r => (
                  <div className="sim-result-tile" key={r.l}>
                    <div className="sim-result-label">{r.l}</div>
                    <div className="sim-result-value" style={{ color: r.c }}>
                      {typeof r.v === 'number' ? (
                        <NumberTicker value={r.v} formatFn={r.l.includes('Variable') ? pct : fmt} />
                      ) : r.v}
                    </div>
                  </div>
                ))}
              </div>

              {result.key_insights?.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3xs)' }}>
                  <div style={{ fontSize: '0.68rem', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--color-muted)' }}>SYNTHETIC INSIGHT LOG</div>
                  {result.key_insights.map((ins: string, i: number) => (
                    <div key={i} style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-2)', padding: '8px 12px', background: 'var(--color-paper-3)', borderRadius: 'var(--radius-card)', borderLeft: '3px solid var(--color-accent)', lineHeight: 1.5 }}>
                      {ins}
                    </div>
                  ))}
                </div>
              )}

              {result.warnings?.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3xs)' }}>
                  <div style={{ fontSize: '0.68rem', fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--color-warning)' }}>SIMULATION ALERTS & RISKS</div>
                  {result.warnings.map((w: string, i: number) => (
                    <div key={i} style={{ fontSize: 'var(--text-xs)', color: 'var(--color-warning)', padding: '8px 12px', background: 'oklch(72% 0.15 75 / 0.08)', borderRadius: 'var(--radius-card)', borderLeft: '3px solid var(--color-warning)', lineHeight: 1.5 }}>
                      {w}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Markdown Rendering Helpers ───────────────────────────────
function parseInlineMarkdown(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const inlineRegex = /(\*\*|`)(.*?)\1/g;
  let match;
  let lastIndex = 0;
  let key = 0;

  while ((match = inlineRegex.exec(text)) !== null) {
    const type = match[1];
    const content = match[2];
    const matchIndex = match.index;

    if (matchIndex > lastIndex) {
      parts.push(text.substring(lastIndex, matchIndex));
    }

    if (type === '**') {
      parts.push(<strong key={`b-${key++}`} style={{ fontWeight: 700, color: 'var(--color-ink)' }}>{content}</strong>);
    } else if (type === '`') {
      parts.push(
        <code key={`c-${key++}`} style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '0.85em',
          background: 'var(--color-paper-3)',
          padding: '2px 4px',
          borderRadius: '4px',
          border: '1px solid var(--color-rule-2)'
        }}>
          {content}
        </code>
      );
    }

    lastIndex = inlineRegex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length > 0 ? parts : [text];
}

function renderMarkdown(text: string): React.ReactNode[] {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];

  let currentTable: string[][] = [];
  let currentList: { items: string[]; type: 'unordered' | 'ordered' } | null = null;
  let keyCounter = 0;

  const flushTable = (key: number) => {
    if (currentTable.length === 0) return null;
    const tableData = [...currentTable];
    currentTable = [];

    let startIndex = 0;
    let headers: string[] = [];

    const isDivider = (row: string[]) => row.every(cell => /^:?-+:?$/.test(cell.trim()));

    if (tableData.length > 1 && isDivider(tableData[1])) {
      headers = tableData[0];
      startIndex = 2;
    } else if (tableData.length > 0) {
      headers = tableData[0];
      startIndex = 1;
    }

    return (
      <div key={`table-${key}`} style={{ overflowX: 'auto', margin: 'var(--space-xs) 0', border: '1px solid var(--color-rule)', borderRadius: 'var(--radius-card)', width: '100%' }}>
        <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', margin: 0 }}>
          {headers.length > 0 && (
            <thead>
              <tr style={{ background: 'var(--color-paper-2)' }}>
                {headers.map((h, i) => (
                  <th key={i} style={{ padding: '8px 12px', borderBottom: '1px solid var(--color-rule)', fontFamily: 'var(--font-mono)', fontSize: '0.68rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--color-muted)', textAlign: 'left' }}>
                    {parseInlineMarkdown(h.trim())}
                  </th>
                ))}
              </tr>
            </thead>
          )}
          <tbody>
            {tableData.slice(startIndex).map((row, rowIndex) => (
              <tr key={rowIndex} style={{ borderBottom: rowIndex === tableData.length - startIndex - 1 ? 'none' : '1px solid var(--color-rule-2)' }}>
                {row.map((cell, cellIndex) => (
                  <td key={cellIndex} style={{ padding: '8px 12px', color: 'var(--color-ink-2)', fontSize: 'var(--text-xs)' }}>
                    {parseInlineMarkdown(cell.trim())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const flushList = (key: number) => {
    if (!currentList) return null;
    const list = { ...currentList };
    currentList = null;

    const ListTag = list.type === 'ordered' ? 'ol' : 'ul';
    const listStyle = list.type === 'ordered'
      ? { listStyleType: 'decimal', paddingLeft: 'var(--space-md)', margin: 'var(--space-2xs) 0' }
      : { listStyleType: 'disc', paddingLeft: 'var(--space-md)', margin: 'var(--space-2xs) 0' };

    return (
      <ListTag key={`list-${key}`} style={listStyle}>
        {list.items.map((item, i) => (
          <li key={i} style={{ margin: '4px 0', color: 'var(--color-ink-2)', fontSize: 'var(--text-xs)', lineHeight: 1.5 }}>
            {parseInlineMarkdown(item)}
          </li>
        ))}
      </ListTag>
    );
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (trimmed.startsWith('|')) {
      if (currentList) {
        elements.push(flushList(keyCounter++));
      }

      const cells = line.split('|').map(c => c.trim());
      if (line.startsWith('|')) cells.shift();
      if (line.endsWith('|')) cells.pop();

      currentTable.push(cells);
      continue;
    } else if (currentTable.length > 0) {
      elements.push(flushTable(keyCounter++));
    }

    const listMatch = trimmed.match(/^([-*+]|\d+\.)\s+(.*)/);
    if (listMatch) {
      const marker = listMatch[1];
      const content = listMatch[2];
      const type = /^\d+/.test(marker) ? 'ordered' : 'unordered';

      if (currentList && currentList.type !== type) {
        elements.push(flushList(keyCounter++));
      }

      if (!currentList) {
        currentList = { items: [], type };
      }

      currentList.items.push(content);
      continue;
    } else if (currentList) {
      elements.push(flushList(keyCounter++));
    }

    if (trimmed.startsWith('#')) {
      const headerLevel = (trimmed.match(/^#+/) || ['#'])[0].length;
      const headerText = trimmed.replace(/^#+\s*/, '');
      const fontSize = headerLevel === 1 ? 'var(--text-md)' : headerLevel === 2 ? 'var(--text-sm)' : 'var(--text-xs)';
      const style = {
        fontFamily: 'var(--font-display)',
        fontWeight: 700,
        color: 'var(--color-ink)',
        margin: 'var(--space-xs) 0 var(--space-2xs)',
        fontSize
      };

      const HeaderTag = `h${Math.min(6, headerLevel + 2)}` as 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
      elements.push(
        <HeaderTag key={keyCounter++} style={style}>
          {parseInlineMarkdown(headerText)}
        </HeaderTag>
      );
      continue;
    }

    if (trimmed === '') {
      continue;
    }

    elements.push(
      <p key={keyCounter++} style={{ margin: '6px 0', color: 'var(--color-ink-2)', lineHeight: 1.6 }}>
        {parseInlineMarkdown(line)}
      </p>
    );
  }

  if (currentTable.length > 0) {
    elements.push(flushTable(keyCounter++));
  }
  if (currentList) {
    elements.push(flushList(keyCounter++));
  }

  return elements;
}

// ─── Chat Page (Terminal Interface) ──────────────────────────
function ChatPage() {
  const [messages, setMessages] = useState<{ role: 'user' | 'ai'; text: string; model?: string }[]>([
    { role: 'ai', text: 'SME OS Intelligence System initialized. Inquire regarding database coordinates, risk indices, liquidity models, or operations.' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const send = async () => {
    if (!input.trim() || loading) return
    const q = input.trim()
    setInput('')
    setMessages(m => [...m, { role: 'user', text: q }])
    setLoading(true)
    try {
      const r = await sendChat(q)
      setMessages(m => [...m, { role: 'ai', text: r.data.response, model: r.data.model_used }])
    } catch {
      setMessages(m => [...m, { role: 'ai', text: 'Simulation engine error. Verify model service runs at target port.' }])
    } finally { setLoading(false) }
  }

  return (
    <div className="page-body" style={{ flex: 1 }}>
      <div className="card reveal" style={{ flex: 1, display: 'flex', flexDirection: 'column', height: 'calc(100vh - 180px)', '--i': 0 } as any}>
        <div className="card-header">
          <div>
            <div className="card-title">AI Engine Chat Console</div>
            <div className="card-subtitle">Context-aware agent execution interface via local Gemma node</div>
          </div>
        </div>

        <div className="chat-messages">
          {messages.map((m, i) => (
            <div className={`chat-bubble ${m.role}`} key={i}>
              {m.role === 'ai' && <div className="bubble-label">{m.model ?? 'SME-OS AI Core'}</div>}
              {renderMarkdown(m.text)}
            </div>
          ))}
          {loading && <div className="chat-bubble ai"><div className="bubble-label">LLM Core processing…</div><div className="spinner" /></div>}
        </div>

        <div className="chat-input-row">
          <input className="chat-input" value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && send()}
            placeholder="Type query to prompt LLM system… e.g. 'What supplier risks exist in database?'" />
          <button className="btn btn-primary" onClick={send} disabled={loading || !input.trim()}><Send size={12} /> Prompt</button>
        </div>
      </div>
    </div>
  )
}

// ─── Executive Brief Page ────────────────────────────────────
function BriefPage() {
  const [brief, setBrief] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const fetch = async () => {
    setLoading(true)
    try { const r = await getExecutiveBrief(); setBrief(r.data) }
    finally { setLoading(false) }
  }

  useEffect(() => {
    fetch()
  }, [])

  return (
    <div className="page-body">
      <div className="card reveal" style={{ '--i': 0 } as any}>
        <div className="card-header">
          <div>
            <div className="card-title">CEO Executive Report Brief</div>
            <div className="card-subtitle">Auto-generated morning executive overview telemetry</div>
          </div>
          <button className="btn btn-primary" onClick={fetch} disabled={loading}>
            {loading ? <><div className="spinner" />Compiling Ledger…</> : <><Sparkles size={14} /> Generate Executive Brief</>}
          </button>
        </div>
        {!brief && !loading && (
          <div className="empty-state" style={{ padding: 'var(--space-xl) 0' }}>
            <div className="empty-icon" style={{ color: 'var(--color-accent)' }}><FileText size={40} /></div>
            <h3>Report Engine Ready</h3>
            <p>Generate summary matrix based on operations data.</p>
          </div>
        )}
        {loading && <BriefPageSkeleton />}
      </div>

      {brief && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
          <div className="card reveal" style={{ '--i': 1 } as any}>
            <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Calendar size={16} style={{ color: 'var(--color-accent)' }} /> Morning Executive Summary
            </div>
            <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-2)', lineHeight: 1.6, padding: 'var(--space-3xs) 0' }}>{brief.morning_summary}</p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--space-sm)' }}>
            {[
              { title: 'Critical Event Risks', items: brief.critical_alerts, color: 'var(--color-error)', bg: 'oklch(62% 0.18 25 / 0.08)', delay: 2 },
              { title: 'Identified Opportunities', items: brief.top_opportunities, color: 'var(--color-success)', bg: 'oklch(68% 0.16 145 / 0.08)', delay: 3 },
              { title: 'Action Ledger Recommendations', items: brief.top_actions, color: 'var(--color-accent)', bg: 'oklch(60% 0.18 250 / 0.08)', delay: 4 },
            ].map(s => (
              <div className="card reveal" key={s.title} style={{ borderLeft: `3px solid ${s.color}`, '--i': s.delay } as any}>
                <div className="card-title" style={{ fontFamily: 'var(--font-display)', marginBottom: 'var(--space-xs)' }}>{s.title}</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2xs)' }}>
                  {(s.items ?? []).map((item: string, i: number) => (
                    <div key={i} style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-2)', padding: '8px 12px', background: s.bg, borderRadius: 'var(--radius-card)', lineHeight: 1.45 }}>
                      {item}
                    </div>
                  ))}
                  {(s.items ?? []).length === 0 && <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-muted)' }}>No items logged.</span>}
                </div>
              </div>
            ))}
          </div>

          <div className="card reveal" style={{ '--i': 5 } as any}>
            <div className="card-title">Macro Health Summary</div>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-2)', lineHeight: 1.6 }}>{brief.business_health_summary}</p>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── CEO Strategic Growth Brief ───────────────────────────────
function CEOStrategicDashboard() {
  const [brief, setBrief] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  const fetch = async () => {
    setLoading(true)
    try {
      const r = await getStrategyBrief()
      setBrief(r.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetch()
  }, [])

  const toggleExpand = (key: string) => {
    setExpanded(prev => ({ ...prev, [key]: !prev[key] }))
  }

  if (loading) return <BriefPageSkeleton />

  return (
    <div className="page-body">
      <div className="card reveal" style={{ '--i': 0 } as any}>
        <div className="card-header">
          <div>
            <div className="card-title">CEO Strategic Growth Dashboard</div>
            <div className="card-subtitle">Synthesized executive consensus briefing citing specialist node justifications</div>
          </div>
          <button className="btn btn-primary" onClick={fetch} disabled={loading}>
            {loading ? <><div className="spinner" /> Synthesizing Strategy…</> : <><Sparkles size={14} /> Refresh Strategic Brief</>}
          </button>
        </div>
        {!brief && !loading && (
          <div className="empty-state" style={{ padding: 'var(--space-xl) 0' }}>
            <div className="empty-icon" style={{ color: 'var(--color-accent)' }}><Bot size={40} /></div>
            <h3>Strategic Dashboard Ready</h3>
            <p>Generate strategy brief to synthesize corporate growth targets.</p>
          </div>
        )}
      </div>

      {brief && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          {[
            {
              key: 'capital_allocation',
              title: 'Capital Allocation Strategy',
              emoji: '💼',
              content: brief.capital_allocation,
              evidence: brief.supporting_evidence?.capital_allocation || 'Derived from current liquidity metrics.'
            },
            {
              key: 'next_product_focus',
              title: 'Next Product & Raw Materials Focus',
              emoji: '📦',
              content: brief.next_product_focus,
              evidence: brief.supporting_evidence?.next_product_focus || 'Derived from procurement cost fluctuations.'
            },
            {
              key: 'cost_reductions',
              title: 'Operational Cost Reductions',
              emoji: '📉',
              content: brief.cost_reductions,
              evidence: brief.supporting_evidence?.cost_reductions || 'Derived from supply chain overhead reports.'
            },
            {
              key: 'promotional_offers',
              title: 'Strategic Promotional Offers',
              emoji: '🎯',
              content: brief.promotional_offers,
              evidence: brief.supporting_evidence?.promotional_offers || 'Derived from customer cohort analysis.'
            }
          ].map((card, idx) => {
            const isExpanded = !!expanded[card.key]
            return (
              <div 
                className="card reveal" 
                key={card.key} 
                style={{ 
                  '--i': idx + 1, 
                  display: 'flex', 
                  flexDirection: 'column', 
                  justifyContent: 'space-between',
                  padding: '20px' 
                } as any}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
                    <span style={{ fontSize: '1.5rem' }}>{card.emoji}</span>
                    <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: 'var(--color-ink)' }}>{card.title}</h3>
                  </div>
                  <p style={{ fontSize: '0.85rem', color: 'var(--color-ink-2)', lineHeight: 1.6, marginBottom: '16px' }}>
                    {card.content}
                  </p>
                </div>
                
                <div style={{ marginTop: 'auto', borderTop: '1px solid var(--color-rule-2)', paddingTop: '12px' }}>
                  <button 
                    onClick={() => toggleExpand(card.key)}
                    style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: '6px', 
                      background: 'none', 
                      border: 'none', 
                      color: 'var(--color-accent)', 
                      fontSize: '0.72rem', 
                      fontWeight: 600, 
                      cursor: 'pointer',
                      padding: 0
                    }}
                  >
                    {isExpanded ? 'Hide Supporting Evidence' : 'Show Supporting Evidence & Citations'}
                  </button>
                  {isExpanded && (
                    <div 
                      style={{ 
                        marginTop: '10px', 
                        padding: '10px 12px', 
                        background: 'var(--color-paper-3)', 
                        borderLeft: '3px solid var(--color-accent)',
                        borderRadius: '4px',
                        fontSize: '0.72rem', 
                        color: 'var(--color-ink-2)',
                        lineHeight: 1.5
                      }}
                    >
                      {card.evidence}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── Decision History Page ────────────────────────────────────
function HistoryPage() {
  const [history, setHistory] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getDecisionHistory().then(r => setHistory(r.data)).finally(() => setLoading(false))
  }, [])

  if (loading) return <HistoryPageSkeleton />

  return (
    <div className="page-body">
      <div className="card reveal" style={{ '--i': 0 } as any}>
        <div className="card-header">
          <div>
            <div className="card-title">Decision Execution History Ledger</div>
            <div className="card-subtitle">Immutable registry of actions executed on AI recommendations</div>
          </div>
        </div>
        {history.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon"><History size={32} /></div>
            <h3>History Clear</h3>
            <p>Decisions ledger is empty. Telemetry will write as actions are taken.</p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>User Decision Action</th>
                <th>Calculated Outcome Description</th>
                <th>Revenue Delta Impact</th>
                <th>User Metadata Feedback</th>
                <th>Execution Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h, i) => (
                <tr key={i}>
                  <td>
                    <span className={`badge ${h.user_action === 'APPROVED' ? 'green' : h.user_action === 'REJECTED' ? 'red' : 'amber'}`}>
                      {h.user_action}
                    </span>
                  </td>
                  <td style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink)' }}>{h.business_outcome ?? '—'}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: h.outcome_revenue_impact >= 0 ? 'var(--color-success)' : 'var(--color-error)' }}>
                    {h.outcome_revenue_impact ? fmt(h.outcome_revenue_impact) : '—'}
                  </td>
                  <td style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-2)' }}>{h.feedback ?? '—'}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: 'var(--color-muted)' }}>
                    {new Date(h.timestamp).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

// ─── Upload Page (Document Ingestion) ──────────────────────────
function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [category, setCategory] = useState('invoice')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [isError, setIsError] = useState(false)
  const [activeSample, setActiveSample] = useState<string | null>(null)

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return
    setLoading(true)
    setMessage('')
    setIsError(false)
    try {
      const res = await uploadFile(category, file)
      setMessage(res.data.message || 'File uploaded successfully!')
      setFile(null)
      const fileInput = document.getElementById('file-input-el') as HTMLInputElement
      if (fileInput) fileInput.value = ''
    } catch (err: any) {
      setIsError(true)
      setMessage(err.response?.data?.detail || 'Error uploading file.')
    } finally {
      setLoading(false)
    }
  }

  const handleSampleClick = async (sampleKey: string) => {
    setActiveSample(sampleKey)
    setMessage('')
    setIsError(false)
    try {
      const res = await uploadSampleDoc(sampleKey)
      setMessage(res.data.message || `Sample '${sampleKey}' queued successfully!`)
    } catch (err: any) {
      setIsError(true)
      setMessage(err.response?.data?.detail || 'Error loading sample document.')
    } finally {
      setActiveSample(null)
    }
  }

  const samples = [
    { key: 'inventory', label: 'Inventory (Excel)', folder: 'inventory/', file: 'inventory.xlsx' },
    { key: 'invoice_001', label: 'ABC Steel Invoice (PDF)', folder: 'invoices/', file: 'invoice_001.pdf' },
    { key: 'invoice_002', label: 'ABC Retail Sales Invoice (PDF)', folder: 'invoices/', file: 'invoice_002.pdf' },
    { key: 'overdue_invoice', label: 'Metro Electronics Overdue Bill (PDF)', folder: 'invoices/', file: 'overdue_invoice.pdf' },
    { key: 'gst_return', label: 'June GST Return (PDF)', folder: 'gst/', file: 'gst_return_june.pdf' },
    { key: 'bank_statement', label: 'July Bank Statement (CSV)', folder: 'bank/', file: 'bank_statement.csv' },
    { key: 'july_statement', label: 'July Bank Statement (Excel)', folder: 'bank/', file: 'july_statement.xlsx' },
    { key: 'price_increase', label: 'ABC Steel 8% Price Hike Notice (PDF)', folder: 'suppliers/', file: 'price_increase_notice.pdf' },
    { key: 'po_2101', label: 'ABC Retail Purchase Order (PDF)', folder: 'purchase_orders/', file: 'po_2101.pdf' },
  ]

  return (
    <div className="page-body">
      <div className="bento-grid">
        {/* Upload Form Card */}
        <div className="col-6 card reveal" style={{ '--i': 0 } as any}>
          <div className="card-header" style={{ marginBottom: 'var(--space-sm)' }}>
            <div>
              <div className="card-title">Document Ingestion Terminal</div>
              <div className="card-subtitle">Upload transaction docs or sheets to update business ledger</div>
            </div>
          </div>

          <form onSubmit={handleUpload} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
            <div className="form-group">
              <label className="form-label" style={{ display: 'block', marginBottom: '6px', fontSize: 'var(--text-xs)', color: 'var(--color-muted)' }}>Document Category</label>
              <select
                className="form-input"
                style={{ width: '100%', padding: '10px', borderRadius: 'var(--radius-card)', background: 'var(--color-paper-3)', border: '1px solid var(--color-rule)', color: 'var(--color-ink)' }}
                value={category}
                onChange={e => setCategory(e.target.value)}
              >
                <option value="invoice">Supplier / Customer Invoice</option>
                <option value="gst">GST Return Summary</option>
                <option value="bank">Bank Statement</option>
                <option value="excel">Excel Bulk Data (Inventory)</option>
                <option value="supplier_notice">Supplier Notice (Price Hike)</option>
                <option value="purchase_order">Customer Purchase Order (PO)</option>
              </select>
            </div>

            <div className="form-group" style={{ marginTop: 'var(--space-2xs)' }}>
              <label className="form-label" style={{ display: 'block', marginBottom: '6px', fontSize: 'var(--text-xs)', color: 'var(--color-muted)' }}>Select Document File</label>
              <div style={{
                border: '2px dashed var(--color-rule)',
                borderRadius: 'var(--radius-card)',
                padding: 'var(--space-md) var(--space-xs)',
                textAlign: 'center',
                background: 'var(--color-paper-3)',
                cursor: 'pointer',
                transition: 'all 120ms ease',
              }} onClick={() => document.getElementById('file-input-el')?.click()}>
                <span style={{ fontSize: '1.5rem', display: 'block', marginBottom: '8px' }}>📂</span>
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-2)' }}>
                  {file ? file.name : 'Click to select file…'}
                </span>
                <input
                  id="file-input-el"
                  type="file"
                  style={{ display: 'none' }}
                  onChange={e => {
                    if (e.target.files && e.target.files.length > 0) {
                      setFile(e.target.files[0])
                    }
                  }}
                />
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%', marginTop: 'var(--space-sm)' }}
              disabled={loading || !file}
            >
              {loading ? <><div className="spinner" /> Ingesting File...</> : <><Upload size={14} style={{ marginRight: '6px' }} /> Ingest Document</>}
            </button>

            {message && (
              <div style={{
                padding: '10px 14px',
                borderRadius: 'var(--radius-card)',
                background: isError ? 'rgba(239,68,68,0.08)' : 'rgba(16,185,129,0.08)',
                border: `1px solid ${isError ? 'var(--color-error)' : 'var(--color-success)'}`,
                color: isError ? 'var(--color-error)' : 'var(--color-success)',
                fontSize: 'var(--text-xs)',
                lineHeight: 1.5,
                marginTop: 'var(--space-xs)',
              }}>
                {message}
              </div>
            )}
          </form>
        </div>

        {/* Demo Fast Ingestion List Card */}
        <div className="col-6 card reveal" style={{ '--i': 1 } as any}>
          <div className="card-header" style={{ marginBottom: 'var(--space-sm)' }}>
            <div>
              <div className="card-title">Demo Quick-Load Panel</div>
              <div className="card-subtitle">Single-click load of local sample business documents</div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2xs)', maxHeight: '380px', overflowY: 'auto', paddingRight: '4px' }}>
            {samples.map(sample => (
              <div key={sample.key} style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: 'var(--space-2xs) var(--space-xs)',
                background: 'var(--color-paper-3)',
                borderRadius: 'var(--radius-card)',
                border: '1px solid var(--color-rule-2)',
              }}>
                <div style={{ marginRight: 'var(--space-xs)' }}>
                  <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-ink)' }}>{sample.label}</div>
                  <div style={{ fontSize: '8px', fontFamily: 'var(--font-mono)', color: 'var(--color-muted)' }}>
                    sample_docs/{sample.folder}{sample.file}
                  </div>
                </div>
                <button
                  className="btn btn-secondary"
                  style={{ fontSize: '9px', padding: '4px 10px', height: '28px', whiteSpace: 'nowrap' }}
                  onClick={() => handleSampleClick(sample.key)}
                  disabled={activeSample !== null}
                >
                  {activeSample === sample.key ? <div className="spinner" /> : 'Load File'}
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// Nav definitions with Lucide Icons
const NAV_CLEAN = [
  { id: 'dashboard' as Page, label: 'Telemetry Dashboard', icon: <LayoutDashboard size={16} />, section: 'Overview' },
  { id: 'materials' as Page, label: 'Raw Materials', icon: <Activity size={16} />, section: undefined },
  { id: 'brief' as Page, label: 'Executive Brief', icon: <FileText size={16} />, section: undefined },
  { id: 'strategy' as Page, label: 'Strategic Brief', icon: <TrendingUp size={16} />, section: undefined },
  { id: 'forecast' as Page, label: 'Predictive Forecast', icon: <TrendingUp size={16} />, section: 'Intelligence' },
  { id: 'risk' as Page, label: 'Risk & Pricing', icon: <ShieldAlert size={16} />, section: undefined },
  { id: 'agents' as Page, label: 'AI Agents Grid', icon: <Bot size={16} />, section: undefined },
  { id: 'simulate' as Page, label: 'Digital Twin Sim', icon: <Sliders size={16} />, section: 'Decision' },
  { id: 'chat' as Page, label: 'AI Chat Core', icon: <MessageSquare size={16} />, section: 'AI Layer' },
  { id: 'upload' as Page, label: 'Document Ingestion', icon: <Upload size={16} />, section: 'Ingestion' },
  { id: 'history' as Page, label: 'Decision History', icon: <History size={16} />, section: 'Audit' },
]

const PAGE_TITLES: Record<Page, string> = {
  dashboard: 'Operations Telemetry Dashboard',
  materials: 'Raw Materials & Pricing Engine',
  forecast: 'Predictive Forecasting Module',
  risk: 'Risk & Pricing Optimisation',
  agents: 'Multi-Agent Network Engine',
  simulate: 'Digital Twin Simulation Console',
  chat: 'AI Core Conversation',
  brief: 'Morning Executive Brief',
  strategy: 'CEO Strategic Growth Brief',
  history: 'Decision Execution Registry',
  upload: 'Automated Document Ingestion Console',
}

export default function App() {
  const [page, setPage] = useState<Page>('dashboard')
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    return (localStorage.getItem('theme') as 'light' | 'dark') || 'dark'
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
    const favicon = document.getElementById('favicon') as HTMLLinkElement | null
    if (favicon) {
      const parent = favicon.parentNode
      if (parent) {
        const newFavicon = document.createElement('link')
        newFavicon.id = 'favicon'
        newFavicon.rel = 'icon'
        newFavicon.type = 'image/png'
        newFavicon.href = (theme === 'dark' ? '/logo-dark.png' : '/logo-light.png') + '?v=' + Date.now()
        parent.replaceChild(newFavicon, favicon)
      }
    }
  }, [theme])

  const renderPage = () => {
    switch (page) {
      case 'dashboard': return <DashboardPage />
      case 'materials': return <MaterialsPage />
      case 'forecast': return <ForecastPage />
      case 'risk': return <RiskPage />
      case 'agents': return <AgentsPage />
      case 'simulate': return <SimulatePage />
      case 'chat': return <ChatPage />
      case 'brief': return <BriefPage />
      case 'strategy': return <CEOStrategicDashboard />
      case 'history': return <HistoryPage />
      case 'upload': return <UploadPage />
    }
  }

  return (
    <div className="app-shell">
      {/* Sidebar Navigation */}
      <nav className="sidebar">
        <div className="sidebar-brand">
          <div className="logo-icon">
            <img
              src="/logo-dark.png"
              alt="Stratify"
              className="logo-img"
              style={{ display: theme === 'dark' ? 'block' : 'none' }}
            />
            <img
              src="/logo-light.png"
              alt="Stratify"
              className="logo-img"
              style={{ display: theme === 'light' ? 'block' : 'none' }}
            />
          </div>
          <div>
            <h1>Stratify</h1>
            <span>Business Core</span>
          </div>
        </div>

        {NAV_CLEAN.map((item, i) => (
          <div key={i}>
            {item.section && <div className="sidebar-section-label">{item.section}</div>}
            <div
              className={`nav-item ${page === item.id ? 'active' : ''}`}
              onClick={() => setPage(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </div>
          </div>
        ))}

        <div className="sidebar-footer">
          <button
            className="theme-toggle"
            onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
            aria-label="Toggle theme"
          >
            <span className="theme-toggle-icon">
              {theme === 'light' ? <Sun size={14} /> : <Moon size={14} />}
            </span>
            <span className="theme-toggle-text">
              {theme === 'light' ? 'Light mode' : 'Dark mode'}
            </span>
          </button>
        </div>
      </nav>

      {/* Main Console Content */}
      <div className="main-content">
        <div className="topbar">
          <div>
            <div className="topbar-title">{PAGE_TITLES[page]}</div>
            <div className="topbar-subtitle">SME Business Operating System</div>
          </div>
        </div>
        <div key={page} className="page-transition-container">
          {renderPage()}
        </div>
      </div>
    </div>
  )
}
