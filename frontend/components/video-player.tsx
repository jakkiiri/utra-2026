"use client"

import React, { useState, useRef, useEffect, useCallback } from "react"
import { Play, Pause, Volume2, VolumeX, Maximize, Settings } from "lucide-react"
import { createPlayer, loadYouTubeAPI, PlayerState } from "@/lib/youtube"
import { useSettings } from "@/contexts/settings-context"
import { SettingsModal } from "./settings-modal"

interface VideoPlayerProps {
  videoId?: string
  onPlayStateChange?: (isPlaying: boolean) => void
  onTimeUpdate?: (currentTime: number) => void
  isNarrating?: boolean
  externalPause?: boolean // Allow external control to pause
  voiceInputActive?: boolean // Lower volume during voice input (so user can still hear context)
  aiSpeaking?: boolean // Lower volume during AI speech
}

export function VideoPlayer({ 
  videoId,
  onPlayStateChange,
  onTimeUpdate,
  isNarrating = false,
  externalPause = false,
  voiceInputActive = false,
  aiSpeaking = false
}: VideoPlayerProps) {
  const { settings } = useSettings()
  const [showSettings, setShowSettings] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [volume, setVolume] = useState(0.66)
  const [isMuted, setIsMuted] = useState(false)
  const [isReady, setIsReady] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  
  const volumeRef = useRef<HTMLDivElement>(null)
  const playerRef = useRef<YT.Player | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const timeUpdateInterval = useRef<NodeJS.Timeout | null>(null)
  
  // Store callbacks in refs to avoid useEffect dependency issues
  const onPlayStateChangeRef = useRef(onPlayStateChange)
  onPlayStateChangeRef.current = onPlayStateChange

  // Initialize YouTube player when videoId changes
  useEffect(() => {
    if (!videoId) return

    let isMounted = true
    
    // Reset ready state when video changes
    setIsReady(false)

    const initPlayer = async () => {
      try {
        console.log('Initializing player for video:', videoId)
        
        await loadYouTubeAPI()
        
        if (!isMounted) return
        
        // Wait for React to render the new element
        await new Promise(resolve => setTimeout(resolve, 200))
        
        // Check for element with retries
        let element = document.getElementById('youtube-player')
        let retries = 0
        while (!element && retries < 5) {
          await new Promise(resolve => setTimeout(resolve, 100))
          element = document.getElementById('youtube-player')
          retries++
        }
        
        if (!element) {
          console.error('YouTube player element not found after retries')
          return
        }
        
        console.log('Found element, creating player')

        // Destroy existing player if any
        if (playerRef.current) {
          try {
            playerRef.current.destroy()
          } catch (e) {
            console.log('Previous player already destroyed')
          }
          playerRef.current = null
          // Wait for cleanup
          await new Promise(resolve => setTimeout(resolve, 100))
        }

        // Create new player
        playerRef.current = await createPlayer('youtube-player', videoId, {
          onReady: (player) => {
            if (!isMounted) return
            console.log('YouTube player ready')
            setIsReady(true)
            setDuration(player.getDuration())
            
            // Ensure audio is set up correctly - unmute and set volume
            try {
              player.unMute()
              player.setVolume(70) // Set to 70% volume
              setVolume(0.7)
              setIsMuted(false)
              console.log('YouTube player audio initialized - volume:', player.getVolume(), 'muted:', player.isMuted())
            } catch (e) {
              console.error('Failed to set audio:', e)
            }
          },
          onStateChange: (state) => {
            if (!isMounted) return
            const playing = PlayerState.isPlaying(state)
            setIsPlaying(playing)
            onPlayStateChangeRef.current?.(playing)

            // Update duration when video is cued or playing
            if ((state === PlayerState.CUED || state === PlayerState.PLAYING) && playerRef.current) {
              const dur = playerRef.current.getDuration()
              if (dur > 0) setDuration(dur)
            }
          },
          onError: (error) => {
            console.error('YouTube player error:', error)
          }
        })
      } catch (error) {
        console.error('Failed to initialize YouTube player:', error)
      }
    }

    initPlayer()

    return () => {
      isMounted = false
      if (playerRef.current) {
        try {
          playerRef.current.destroy()
        } catch (e) {
          // Player might already be destroyed
        }
        playerRef.current = null
      }
    }
  }, [videoId])

  // Handle external pause request (e.g., when voice is detected)
  useEffect(() => {
    if (externalPause && playerRef.current && isPlaying) {
      playerRef.current.pauseVideo()
    }
  }, [externalPause, isPlaying])

  // Store user's preferred volume before any adjustments
  const userVolumeRef = useRef<number>(0.66)

  // Keep ref updated with user's volume preference (when not being adjusted externally)
  useEffect(() => {
    if (!voiceInputActive && !aiSpeaking) {
      userVolumeRef.current = volume
    }
  }, [volume, voiceInputActive, aiSpeaking])

  // Handle voice input - LOWER volume (not mute) so user can still hear context
  useEffect(() => {
    if (playerRef.current && isReady) {
      if (voiceInputActive) {
        console.log(`Voice input active - lowering video volume to ${settings.volumeDuckingPercent}%`)
        playerRef.current.unMute()
        playerRef.current.setVolume(settings.volumeDuckingPercent) // Lower volume during voice input (same as AI speaking)
      } else if (!isMuted && !aiSpeaking) {
        // Restore full volume when voice input ends (if not AI speaking and user hasn't muted)
        console.log('Voice input ended - restoring volume to', userVolumeRef.current * 100)
        playerRef.current.setVolume(userVolumeRef.current * 100)
      }
    }
  }, [voiceInputActive, isReady, isMuted, aiSpeaking, settings.volumeDuckingPercent])

  // Handle AI speaking - LOWER volume (not mute)
  useEffect(() => {
    if (playerRef.current && isReady && !voiceInputActive) {
      if (aiSpeaking) {
        console.log(`AI speaking - lowering video volume to ${settings.volumeDuckingPercent}%`)
        playerRef.current.unMute()
        playerRef.current.setVolume(settings.volumeDuckingPercent) // Lower volume during AI speech (configurable)
      } else if (!isMuted) {
        // Restore user's volume when AI stops speaking
        console.log('AI stopped - restoring volume to', userVolumeRef.current * 100)
        playerRef.current.setVolume(userVolumeRef.current * 100)
      }
    }
  }, [aiSpeaking, isReady, isMuted, voiceInputActive, settings.volumeDuckingPercent])

  // Update volume when changed
  useEffect(() => {
    if (playerRef.current && isReady) {
      playerRef.current.setVolume(volume * 100)
    }
  }, [volume, isReady])

  // Update mute state
  useEffect(() => {
    if (playerRef.current && isReady) {
      if (isMuted) {
        playerRef.current.mute()
      } else {
        playerRef.current.unMute()
      }
    }
  }, [isMuted, isReady])

  // Track playback time
  useEffect(() => {
    if (isPlaying && playerRef.current) {
      timeUpdateInterval.current = setInterval(() => {
        if (playerRef.current) {
          const time = playerRef.current.getCurrentTime()
          setCurrentTime(time)
          onTimeUpdate?.(time)
        }
      }, 1000) // Update every second
    } else {
      if (timeUpdateInterval.current) {
        clearInterval(timeUpdateInterval.current)
        timeUpdateInterval.current = null
      }
    }

    return () => {
      if (timeUpdateInterval.current) {
        clearInterval(timeUpdateInterval.current)
      }
    }
  }, [isPlaying, onTimeUpdate])

  const togglePlay = useCallback(() => {
    console.log('Toggle play clicked, playerRef:', !!playerRef.current, 'isPlaying:', isPlaying, 'isReady:', isReady)
    
    if (!playerRef.current) {
      console.log('No player ref available')
      return
    }
    
    try {
      if (isPlaying) {
        playerRef.current.pauseVideo()
      } else {
        playerRef.current.playVideo()
      }
    } catch (e) {
      console.error('Error controlling player:', e)
    }
  }, [isPlaying, isReady])

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

  const handleFullscreen = () => {
    if (containerRef.current) {
      if (document.fullscreenElement) {
        document.exitFullscreen()
      } else {
        containerRef.current.requestFullscreen()
      }
    }
  }

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <>
      {/* Video Container */}
      <div 
        ref={containerRef}
        className="fixed inset-0 z-0 overflow-hidden"
      >
        {/* YouTube Player or Placeholder */}
        {videoId ? (
          <div 
            key={videoId}
            id="youtube-player" 
            className="absolute inset-0 w-full h-full"
          />
        ) : (
          <div 
            className="absolute inset-0 bg-cover bg-center transition-transform duration-1000"
            style={{
              backgroundImage: `url("https://lh3.googleusercontent.com/aida-public/AB6AXuDOyTIFBm737BuKX29octXW9k-nXcuFFb_JLrgX-b8Pz1nXJK5Si9tdU3xHCGv5z-VnryA0p4Mmfq8wmAAYfx832UTwAOKw2dqA2sdju8w48ofbV4PbTM2L5CLc6PH2aXe2CbCyNGAFdE9JNy7WayT468R9vReKFNR16u4VJk3aleoRDi_U4ZXkqUErFgNHUGH5EFZblYLHvuM-g9_XSQLpKKmSx_p7LP_jmYwsJkwuI_w1bfBd1qVZrkiTdBiiUbZwVZKDqrSbQQ")`,
              transform: isPlaying ? 'scale(1.02)' : 'scale(1)'
            }}
          />
        )}
        
        <div className="absolute inset-0 cinematic-vignette pointer-events-none" />
        <div className="absolute inset-0 bg-black/20 pointer-events-none" />

        {/* Glow ring when agent is thinking */}
        {isNarrating && (
          <div className="absolute inset-0 pointer-events-none z-40">
            <svg className="w-full h-full">
              <rect
                x="8"
                y="8"
                width="calc(100% - 16px)"
                height="calc(100% - 16px)"
                fill="none"
                stroke="url(#lavender-gradient)"
                strokeWidth="4"
                rx="12"
                className="animate-pulse"
                style={{ animationDuration: '2s' }}
              />
              <defs>
                <linearGradient id="lavender-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#9b87f5" stopOpacity="0.8" />
                  <stop offset="50%" stopColor="#7c4dff" stopOpacity="0.9" />
                  <stop offset="100%" stopColor="#9b87f5" stopOpacity="0.8" />
                </linearGradient>
              </defs>
            </svg>
          </div>
        )}

        {/* Narration indicator overlay */}
        {isNarrating && (
          <div className="absolute bottom-32 left-1/2 -translate-x-1/2 flex items-center gap-3 glass-overlay px-6 py-3 rounded-full pointer-events-none z-30">
            <div className="flex items-center gap-1">
              <span className="size-2 bg-lavender-400 rounded-full animate-pulse" />
              <span className="size-2.5 bg-lavender-400 rounded-full animate-pulse delay-75" />
              <span className="size-3 bg-lavender-400 rounded-full animate-pulse delay-150" />
              <span className="size-2.5 bg-lavender-400 rounded-full animate-pulse delay-75" />
              <span className="size-2 bg-lavender-400 rounded-full animate-pulse" />
            </div>
            <span className="text-sm text-white/80 font-medium">AI is responding...</span>
          </div>
        )}

        {/* Time display for accessibility */}
        {videoId && isReady && duration > 0 && (!isPlaying || settings.showTimerDuringPlayback) && (
          <div className="absolute top-20 right-4 glass-overlay px-4 py-2 rounded-lg pointer-events-none z-30">
            <span className="text-sm text-white/80 font-mono">
              {formatTime(currentTime)} / {formatTime(duration)}
            </span>
          </div>
        )}
      </div>

      {/* Center Play Button - Only shown when no video is loaded (use YouTube's native controls otherwise) */}
      {!videoId && (
        <div className="fixed inset-0 flex items-center justify-center pointer-events-none z-20">
          <button 
            onClick={togglePlay}
            className="pointer-events-auto size-20 lg:size-24 rounded-full bg-white/10 backdrop-blur-xl flex items-center justify-center text-white border border-white/20 hover:bg-white/20 transition-all group"
            aria-label="Play video"
          >
            <Play className="size-8 lg:size-12 ml-1 group-hover:scale-110 transition-transform" />
          </button>
        </div>
      )}

      {/* Bottom Left Controls - Volume */}
      <div className="fixed bottom-6 lg:bottom-10 left-4 lg:left-10 z-50 flex items-center gap-3">
        <button 
          onClick={toggleMute}
          className="size-10 lg:size-12 rounded-full glass-overlay flex items-center justify-center hover:bg-white/20 transition-all text-white/80"
          aria-label={isMuted ? "Unmute video" : "Mute video"}
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
          aria-label="Volume control"
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
          onClick={() => setShowSettings(true)}
          className="size-10 lg:size-12 rounded-full glass-overlay flex items-center justify-center hover:bg-white/20 transition-all text-white/80"
          aria-label="Settings"
        >
          <Settings className="size-4 lg:size-5" />
        </button>
        <button
          onClick={handleFullscreen}
          className="size-10 lg:size-12 rounded-full glass-overlay flex items-center justify-center hover:bg-white/20 transition-all text-white/80"
          aria-label="Toggle fullscreen"
        >
          <Maximize className="size-4 lg:size-5" />
        </button>
      </div>

      {/* Settings Modal */}
      <SettingsModal isOpen={showSettings} onClose={() => setShowSettings(false)} />
    </>
  )
}

// Extend Window interface for YT
declare global {
  interface Window {
    YT: typeof YT
  }
}
