"use client"

import { useEffect, useState } from "react"

interface VoiceWaveformProps {
  isActive: boolean
  mode?: "dictation"  // Only one mode now - purple dictation
}

export function VoiceWaveform({ isActive }: VoiceWaveformProps) {
  const [bars, setBars] = useState<number[]>([])

  useEffect(() => {
    // Initialize with 20 bars
    const initialBars = Array(20).fill(0).map(() => Math.random() * 0.3 + 0.1)
    setBars(initialBars)

    if (!isActive) return

    // Animate bars when active
    const interval = setInterval(() => {
      setBars(prev => prev.map(() => Math.random() * 0.8 + 0.2))
    }, 100)

    return () => clearInterval(interval)
  }, [isActive])

  return (
    <div className="flex items-center justify-center gap-1 h-12 w-full px-4">
      {bars.map((height, index) => (
        <div
          key={index}
          className={`w-1 rounded-full transition-all duration-100 bg-lavender-400 ${isActive ? 'shadow-lavender-400/50' : ''}`}
          style={{
            height: `${height * 100}%`,
            opacity: isActive ? 0.8 : 0.3,
            boxShadow: isActive ? `0 0 8px currentColor` : 'none'
          }}
        />
      ))}
    </div>
  )
}
