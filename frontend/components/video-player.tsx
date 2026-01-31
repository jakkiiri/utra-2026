"use client"

import React from "react"

import { useState, useRef, useEffect } from "react"
import { Play, Pause, Volume2, VolumeX, Maximize, Settings } from "lucide-react"

interface VideoPlayerProps {
  backgroundImage?: string
  onPlayStateChange?: (isPlaying: boolean) => void
  isNarrating?: boolean
}

export function VideoPlayer({ 
  backgroundImage,
  onPlayStateChange,
  isNarrating = false
}: VideoPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [volume, setVolume] = useState(0.66)
  const [isMuted, setIsMuted] = useState(false)
  const volumeRef = useRef<HTMLDivElement>(null)

  const togglePlay = () => {
    const newState = !isPlaying
    setIsPlaying(newState)
    onPlayStateChange?.(newState)
  }

  const toggleMute = () => {
    setIsMuted(!isMuted)
  }

  const handleVolumeChange = (e: React.MouseEvent<HTMLDivElement>) => {
    if (volumeRef.current) {
      const rect = volumeRef.current.getBoundingClientRect()
      const x = e.clientX - rect.left
      const newVolume = Math.max(0, Math.min(1, x / rect.width))
      setVolume(newVolume)
      if (newVolume > 0 && isMuted) {
        setIsMuted(false)
      }
    }
  }

  // Simulated play state for demo
  useEffect(() => {
    if (isPlaying) {
      // In a real app, this would connect to a video stream
      console.log("[v0] Video playback started")
    }
  }, [isPlaying])

  return (
    <>
      {/* Background with cinematic effects */}
      <div className="fixed inset-0 z-0 overflow-hidden">
        <div 
          className="absolute inset-0 bg-cover bg-center transition-transform duration-1000"
          style={{
            backgroundImage: backgroundImage 
              ? `url("${backgroundImage}")` 
              : `url("https://lh3.googleusercontent.com/aida-public/AB6AXuDOyTIFBm737BuKX29octXW9k-nXcuFFb_JLrgX-b8Pz1nXJK5Si9tdU3xHCGv5z-VnryA0p4Mmfq8wmAAYfx832UTwAOKw2dqA2sdju8w48ofbV4PbTM2L5CLc6PH2aXe2CbCyNGAFdE9JNy7WayT468R9vReKFNR16u4VJk3aleoRDi_U4ZXkqUErFgNHUGH5EFZblYLHvuM-g9_XSQLpKKmSx_p7LP_jmYwsJkwuI_w1bfBd1qVZrkiTdBiiUbZwVZKDqrSbQQ")`,
            transform: isPlaying ? 'scale(1.02)' : 'scale(1)'
          }}
        />
        <div className="absolute inset-0 cinematic-vignette" />
        <div className="absolute inset-0 bg-black/20" />
        
        {/* Narration indicator overlay */}
        {isNarrating && (
          <div className="absolute bottom-32 left-1/2 -translate-x-1/2 flex items-center gap-3 glass-overlay px-6 py-3 rounded-full">
            <div className="flex items-center gap-1">
              <span className="size-2 bg-lavender-400 rounded-full animate-pulse" />
              <span className="size-2.5 bg-lavender-400 rounded-full animate-pulse delay-75" />
              <span className="size-3 bg-lavender-400 rounded-full animate-pulse delay-150" />
              <span className="size-2.5 bg-lavender-400 rounded-full animate-pulse delay-75" />
              <span className="size-2 bg-lavender-400 rounded-full animate-pulse" />
            </div>
            <span className="text-sm text-white/80 font-medium">AI is narrating...</span>
          </div>
        )}
      </div>

      {/* Center Play Button */}
      <div className="flex-1 flex items-center justify-center pointer-events-none">
        <button 
          onClick={togglePlay}
          className="pointer-events-auto size-20 lg:size-24 rounded-full bg-white/10 backdrop-blur-xl flex items-center justify-center text-white border border-white/20 hover:bg-white/20 transition-all group"
          aria-label={isPlaying ? "Pause stream" : "Play stream"}
        >
          {isPlaying ? (
            <Pause className="size-8 lg:size-12 group-hover:scale-110 transition-transform" />
          ) : (
            <Play className="size-8 lg:size-12 ml-1 group-hover:scale-110 transition-transform" />
          )}
        </button>
      </div>

      {/* Bottom Left Controls - Volume */}
      <div className="fixed bottom-6 lg:bottom-10 left-4 lg:left-10 z-50 flex items-center gap-3">
        <button 
          onClick={toggleMute}
          className="size-10 lg:size-12 rounded-full glass-overlay flex items-center justify-center hover:bg-white/20 transition-all text-white/80"
          aria-label={isMuted ? "Unmute" : "Mute"}
        >
          {isMuted || volume === 0 ? (
            <VolumeX className="size-4 lg:size-5" />
          ) : (
            <Volume2 className="size-4 lg:size-5" />
          )}
        </button>
        <div 
          ref={volumeRef}
          onClick={handleVolumeChange}
          className="h-1 w-24 lg:w-32 bg-white/20 rounded-full relative overflow-hidden cursor-pointer group"
          role="slider"
          aria-label="Volume"
          aria-valuenow={Math.round(volume * 100)}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div 
            className="absolute top-0 left-0 h-full bg-lavender-400 transition-all"
            style={{ width: `${(isMuted ? 0 : volume) * 100}%` }}
          />
        </div>
      </div>

      {/* Bottom Right Controls - Settings & Fullscreen */}
      <div className="fixed bottom-6 lg:bottom-10 right-4 lg:right-10 z-50 flex items-center gap-2 lg:gap-3">
        <button 
          className="size-10 lg:size-12 rounded-full glass-overlay flex items-center justify-center hover:bg-white/20 transition-all text-white/80"
          aria-label="Settings"
        >
          <Settings className="size-4 lg:size-5" />
        </button>
        <button 
          className="size-10 lg:size-12 rounded-full glass-overlay flex items-center justify-center hover:bg-white/20 transition-all text-white/80"
          aria-label="Fullscreen"
        >
          <Maximize className="size-4 lg:size-5" />
        </button>
      </div>
    </>
  )
}
