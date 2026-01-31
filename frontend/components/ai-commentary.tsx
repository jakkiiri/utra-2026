"use client"

import { useState, useRef, useEffect } from "react"
import { Sparkles, History, ChevronLeft, ChevronRight } from "lucide-react"

export interface CommentaryItem {
  id: string
  type: 'market_shift' | 'historical' | 'analysis' | 'narration'
  timestamp: string
  title?: string
  content: string
  highlight?: {
    value: string
    label?: string
  }
  comparison?: {
    current: number
    record: number
    note: string
  }
}

interface AICommentaryProps {
  items: CommentaryItem[]
  isLive: boolean
}

export function AICommentary({ items, isLive }: AICommentaryProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const prevItemsLengthRef = useRef(items.length)

  // Auto-scroll to top when new items are added (since newest items are at the top)
  useEffect(() => {
    if (items.length > prevItemsLengthRef.current && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTo({
        top: 0,
        behavior: 'smooth'
      })
    }
    prevItemsLengthRef.current = items.length
  }, [items.length])

  if (isCollapsed) {
    return (
      <button
        onClick={() => setIsCollapsed(false)}
        className="glass-overlay p-2 rounded-xl flex items-center justify-center hover:bg-white/20 transition-all"
        aria-label="Expand AI commentary"
      >
        <ChevronLeft className="size-5 text-white/80" />
      </button>
    )
  }

  return (
    <aside className="w-full lg:w-72 flex flex-col gap-2 lg:gap-3">
      {/* Header with collapse button */}
      <div className="glass-overlay lavender-glow p-3 rounded-xl lg:rounded-2xl flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="size-4 text-lavender-400 fill-lavender-400" />
          <h2 className="text-[10px] lg:text-xs font-bold tracking-wide text-white">AI COMMENTARY</h2>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1">
            <span className={`size-1.5 rounded-full ${isLive ? 'bg-emerald-400' : 'bg-white/40'}`} />
            <span className={`text-[9px] font-bold uppercase ${isLive ? 'text-emerald-400' : 'text-white/40'}`}>
              {isLive ? 'Live' : 'Paused'}
            </span>
          </div>
          <button
            onClick={() => setIsCollapsed(true)}
            className="hidden lg:flex p-1 rounded hover:bg-white/10 transition-all"
            aria-label="Collapse AI commentary"
          >
            <ChevronRight className="size-3 text-white/60" />
          </button>
        </div>
      </div>

      {/* Commentary Feed - Compact and auto-scrolls */}
      <div 
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto space-y-2 custom-scrollbar pr-1 max-h-[300px] lg:max-h-[50vh]"
        role="log"
        aria-live="polite"
        aria-label="AI Commentary feed"
      >
        {items.map((item) => (
          <CommentaryCard key={item.id} item={item} />
        ))}
      </div>
    </aside>
  )
}

function CommentaryCard({ item }: { item: CommentaryItem }) {
  if (item.type === 'market_shift') {
    return (
      <div className="glass-overlay p-3 rounded-xl border-l-2 border-l-emerald-400/50">
        <div className="flex justify-between items-center mb-1">
          <span className="text-[9px] font-bold text-emerald-300 uppercase tracking-widest">
            Status
          </span>
          <span className="text-[9px] text-white/40">{item.timestamp}</span>
        </div>
        <p className="text-xs text-white/90 leading-relaxed">
          {item.content}
          {item.highlight && (
            <span className="text-emerald-400 font-bold"> {item.highlight.value}</span>
          )}
        </p>
      </div>
    )
  }

  if (item.type === 'historical' && item.comparison) {
    return (
      <div className="glass-overlay p-3 rounded-xl">
        <div className="flex items-center gap-2 mb-2">
          <div className="size-6 rounded-lg bg-white/10 flex items-center justify-center border border-white/10">
            <History className="size-3 text-lavender-300" />
          </div>
          <div>
            <p className="text-[9px] font-bold text-white/40 uppercase tracking-widest">
              Historical
            </p>
            <h4 className="text-xs font-bold text-white">{item.title}</h4>
          </div>
        </div>
        <div className="flex justify-between items-end border-b border-white/10 pb-2 mb-2">
          <div>
            <p className="text-[9px] text-white/40">Current</p>
            <p className="text-base font-bold text-lavender-300">{item.comparison.current.toFixed(2)}</p>
          </div>
          <div className="text-right">
            <p className="text-[9px] text-white/40">Record</p>
            <p className="text-base font-bold text-white/20">{item.comparison.record.toFixed(2)}</p>
          </div>
        </div>
        <p className="text-[10px] italic text-white/50">{`"${item.comparison.note}"`}</p>
      </div>
    )
  }

  if (item.type === 'analysis') {
    return (
      <div className="glass-overlay p-3 rounded-xl">
        <p className="text-[9px] font-bold text-lavender-300 uppercase tracking-widest mb-1">
          AI Response
        </p>
        <p className="text-xs leading-relaxed text-white/80">
          {item.content}
        </p>
      </div>
    )
  }

  // Default narration type
  return (
    <div className="glass-overlay p-3 rounded-xl border-l-2 border-l-lavender-400/50">
      <div className="flex justify-between items-center mb-1">
        <span className="text-[9px] font-bold text-lavender-300 uppercase tracking-widest">
          Narration
        </span>
        <span className="text-[9px] text-white/40">{item.timestamp}</span>
      </div>
      <p className="text-xs text-white/90 leading-relaxed">{item.content}</p>
    </div>
  )
}
