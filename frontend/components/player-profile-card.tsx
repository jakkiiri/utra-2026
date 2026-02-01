"use client"

import { User, ExternalLink } from "lucide-react"

interface PlayerProfileCardProps {
  title: string
  content: string
  timestamp: string
  highlight?: {
    value: string // URL
    label?: string
    image?: string // Player image URL
    stats?: string[] // Array of stat bullets
  }
}

export function PlayerProfileCard({ title, content, timestamp, highlight }: PlayerProfileCardProps) {
  return (
    <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-4 border border-white/10 hover:border-lavender-400/30 transition-all">
      {/* Header with timestamp */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-white/60 text-xs">
          <User className="size-3" />
          <span>PLAYER PROFILE</span>
        </div>
        <span className="text-white/40 text-xs font-mono">{timestamp}</span>
      </div>

      {/* Player Image and Name */}
      <div className="flex gap-3 mb-3">
        {highlight?.image ? (
          <img
            src={highlight.image}
            alt={title}
            className="size-16 rounded-full object-cover border-2 border-lavender-400/30"
            onError={(e) => {
              // Fallback to placeholder if image fails
              e.currentTarget.style.display = 'none'
            }}
          />
        ) : (
          <div className="size-16 rounded-full bg-lavender-500/20 flex items-center justify-center border-2 border-lavender-400/30">
            <User className="size-8 text-lavender-400" />
          </div>
        )}

        <div className="flex-1">
          <h3 className="text-white font-semibold text-base leading-tight mb-1">
            {title}
          </h3>
          <p className="text-white/70 text-sm leading-snug">
            {content}
          </p>
        </div>
      </div>

      {/* Stats */}
      {highlight?.stats && highlight.stats.length > 0 && (
        <div className="space-y-1 mb-3 pl-1">
          {highlight.stats.map((stat, index) => (
            <div key={index} className="flex items-start gap-2 text-sm text-white/60">
              <span className="text-lavender-400 mt-0.5">•</span>
              <span className="flex-1">{stat}</span>
            </div>
          ))}
        </div>
      )}

      {/* View Profile Link */}
      {highlight?.value && (
        <a
          href={highlight.value}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 text-lavender-400 hover:text-lavender-300 text-sm transition-colors group"
        >
          <span>{highlight.label || "View Full Profile"}</span>
          <ExternalLink className="size-3 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
        </a>
      )}
    </div>
  )
}
