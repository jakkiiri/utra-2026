"use client"

import { useState } from "react"
import { TrendingUp, AlertTriangle, ChevronLeft, ChevronRight } from "lucide-react"

interface EventSidebarProps {
  eventName: string
  eventSubtitle: string
  venue: string
  isLive: boolean
  winProbability: number
  probabilityChange: number
  technicalScore: number
  riskWarning?: {
    title: string
    description: string
    probability: number
  }
}

export function EventSidebar({
  eventName,
  eventSubtitle,
  venue,
  isLive,
  winProbability,
  probabilityChange,
  technicalScore,
  riskWarning
}: EventSidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)

  if (isCollapsed) {
    return (
      <div className="flex items-center gap-2">
        <button
          onClick={() => setIsCollapsed(false)}
          className="glass-overlay p-2 rounded-xl flex items-center justify-center hover:bg-white/20 transition-all"
          aria-label="Expand event info"
        >
          <ChevronRight className="size-5 text-white/80" />
        </button>
        <span className="glass-overlay px-3 py-2 rounded-lg text-xs text-white whitespace-nowrap pointer-events-none">
          Event Info
        </span>
      </div>
    )
  }

  return (
    <aside className="w-full lg:w-64 flex flex-col gap-3 lg:gap-4">
      {/* Collapse button */}
      <button
        onClick={() => setIsCollapsed(true)}
        className="hidden lg:flex glass-overlay p-1.5 rounded-lg items-center justify-center hover:bg-white/20 transition-all self-end"
        aria-label="Collapse event info"
      >
        <ChevronLeft className="size-4 text-white/60" />
      </button>

      {/* Event Info Card */}
      <div className="glass-overlay lavender-glow p-3 lg:p-4 rounded-xl lg:rounded-2xl">
        <div className="bg-white/10 w-fit px-2 py-0.5 rounded-full text-[9px] font-bold text-lavender-300 border border-lavender-400/30 mb-2">
          EVENT INFO
        </div>
        <h1 className="text-base lg:text-lg font-light leading-tight text-white">
          {eventName}: <br/>
          <span className="font-bold text-sm lg:text-base">{eventSubtitle}</span>
        </h1>
        <div className="flex items-center gap-2 mt-2">
          {isLive && (
            <span className="flex items-center gap-1 px-2 py-0.5 bg-red-500 rounded-full text-[9px] font-bold text-white uppercase tracking-wider">
              <span className="size-1 bg-white rounded-full animate-pulse" />
              Live
            </span>
          )}
          <span className="text-[10px] text-white/60">{venue}</span>
        </div>
      </div>

      {/* Live Betting Odds Card - Compact */}
      <div className="glass-overlay lavender-glow p-3 lg:p-4 rounded-xl lg:rounded-2xl">
        <p className="text-[9px] uppercase tracking-widest text-white/50 font-bold mb-1">
          Live Betting Odds
        </p>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold text-white">{winProbability}%</span>
          <span className={`text-xs font-bold flex items-center tracking-tight ${
            probabilityChange >= 0 ? 'text-emerald-400' : 'text-red-400'
          }`}>
            <TrendingUp className="size-3" />
            {probabilityChange >= 0 ? '+' : ''}{probabilityChange}%
          </span>
        </div>
        <div className="mt-2 pt-2 border-t border-white/10">
          <p className="text-[9px] uppercase tracking-widest text-white/50 font-bold mb-1">
            Technical Estimate
          </p>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-light text-white">{technicalScore.toFixed(2)}</span>
            <span className="text-white/40 text-[9px]">TES</span>
          </div>
        </div>
      </div>

      {/* Risk Warning Card - Compact */}
      {riskWarning && (
        <div className="glass-overlay lavender-glow p-3 lg:p-4 rounded-xl lg:rounded-2xl border-l-2 border-l-amber-400/50">
          <div className="flex items-center gap-1.5 mb-1.5">
            <AlertTriangle className="size-3 text-amber-400" />
            <span className="text-[9px] font-bold text-amber-200 uppercase tracking-wider">
              {riskWarning.title}
            </span>
          </div>
          <p className="text-xs text-white/80 leading-relaxed">
            {riskWarning.description.replace(
              `${riskWarning.probability}%`,
              ''
            )}
            <span className="text-amber-400 font-bold">{riskWarning.probability}%</span> error risk.
          </p>
        </div>
      )}
    </aside>
  )
}
