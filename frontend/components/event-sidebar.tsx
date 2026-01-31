"use client"

import { TrendingUp, AlertTriangle } from "lucide-react"

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
  return (
    <aside className="w-full lg:w-80 flex flex-col gap-4 lg:gap-6">
      {/* Event Info Card */}
      <div className="glass-overlay lavender-glow p-4 lg:p-6 rounded-2xl lg:rounded-3xl">
        <div className="bg-white/10 w-fit px-3 py-1 rounded-full text-[10px] font-bold text-lavender-300 border border-lavender-400/30 mb-3 lg:mb-4">
          EVENT INFO
        </div>
        <h1 className="text-xl lg:text-2xl font-light leading-tight text-white">
          {eventName}: <br/>
          <span className="font-bold">{eventSubtitle}</span>
        </h1>
        <div className="flex items-center gap-3 mt-3 lg:mt-4">
          {isLive && (
            <span className="flex items-center gap-1.5 px-2.5 py-1 bg-red-500 rounded-full text-[10px] font-bold text-white uppercase tracking-wider">
              <span className="size-1.5 bg-white rounded-full animate-pulse" />
              Live
            </span>
          )}
          <span className="text-xs text-white/60">{venue}</span>
        </div>
      </div>

      {/* Live Betting Odds Card */}
      <div className="glass-overlay lavender-glow p-4 lg:p-6 rounded-2xl lg:rounded-3xl">
        <p className="text-[10px] uppercase tracking-widest text-white/50 font-bold mb-2 lg:mb-3">
          Live Betting Odds
        </p>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl lg:text-4xl font-bold text-white">{winProbability}%</span>
          <span className={`text-sm font-bold flex items-center tracking-tight ${
            probabilityChange >= 0 ? 'text-emerald-400' : 'text-red-400'
          }`}>
            <TrendingUp className="size-4" />
            {probabilityChange >= 0 ? '+' : ''}{probabilityChange}%
          </span>
        </div>
        <div className="mt-3 lg:mt-4 pt-3 lg:pt-4 border-t border-white/10">
          <p className="text-[10px] uppercase tracking-widest text-white/50 font-bold mb-2">
            Technical Estimate
          </p>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl lg:text-3xl font-light text-white">{technicalScore.toFixed(2)}</span>
            <span className="text-white/40 text-[10px]">TES</span>
          </div>
        </div>
      </div>

      {/* Risk Warning Card */}
      {riskWarning && (
        <div className="glass-overlay lavender-glow p-4 lg:p-6 rounded-2xl lg:rounded-3xl border-l-4 border-l-amber-400/50">
          <div className="flex items-center gap-2 mb-2 lg:mb-3">
            <AlertTriangle className="size-4 lg:size-5 text-amber-400" />
            <span className="text-[10px] font-bold text-amber-200 uppercase tracking-wider">
              {riskWarning.title}
            </span>
          </div>
          <p className="text-sm text-white/80 leading-relaxed">
            {riskWarning.description.replace(
              `${riskWarning.probability}%`,
              ''
            )}
            <span className="text-amber-400 font-bold">{riskWarning.probability}%</span> probability of error.
          </p>
        </div>
      )}
    </aside>
  )
}
