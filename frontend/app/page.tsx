"use client"

import { useState, useCallback, useRef, useEffect } from "react"
import { StreamHeader } from "@/components/stream-header"
import { EventSidebar } from "@/components/event-sidebar"
import { AICommentary, type CommentaryItem } from "@/components/ai-commentary"
import { AIChatInput } from "@/components/ai-chat-input"
import { VideoPlayer } from "@/components/video-player"
import { VideoUrlInput } from "@/components/video-url-input"
import { SuggestedPrompts } from "@/components/suggested-prompts"
import {
  askQuestion,
  VideoLoadResponse,
  wsClient,
  WebSocketMessage
} from "@/lib/api"
import { useSettings } from "@/contexts/settings-context"
import {
  startPersistentScreenCapture,
  captureFromPersistentStream,
  stopPersistentScreenCapture,
  isScreenCaptureActive
} from "@/lib/screenshot"

export default function SportsNarratorPage() {
  const { settings } = useSettings()

  // Video state
  const [videoId, setVideoId] = useState<string | null>(null)
  const [isLive, setIsLive] = useState(false)

  // Playback state
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [shouldPause, setShouldPause] = useState(false)
  const [shouldMuteVideo, setShouldMuteVideo] = useState(false)

  // AI state
  const [isProcessing, setIsProcessing] = useState(false)
  const [isNarrating, setIsNarrating] = useState(false)
  const [isListeningToVoice, setIsListeningToVoice] = useState(false)
  const [isPlayingAIAudio, setIsPlayingAIAudio] = useState(false)

  // Screen capture state
  const [screenCaptureActive, setScreenCaptureActive] = useState(false)
  const [showScreenCapturePrompt, setShowScreenCapturePrompt] = useState(true)
  
  // Commentary feed
  const [commentary, setCommentary] = useState<CommentaryItem[]>([
    {
      id: '1',
      type: 'analysis',
      timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
      content: 'Welcome to WinterStream AI! Paste a YouTube video URL above to get started. I\'ll help you understand what\'s happening in the event.'
    }
  ])

  // Event data (can be updated based on video metadata)
  const [eventData, setEventData] = useState({
    eventName: "Winter Olympics",
    eventSubtitle: "Event",
    venue: "Loading...",
    isLive: false,
    winProbability: 0,
    probabilityChange: 0,
    technicalScore: 0,
    riskWarning: undefined as { title: string; description: string; probability: number } | undefined
  })

  // Audio playback ref - connected to DOM audio element
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // Debug: log mute state changes
  useEffect(() => {
    console.log('[Page] Mute state - listening:', isListeningToVoice, 'AI playing:', isPlayingAIAudio)
  }, [isListeningToVoice, isPlayingAIAudio])

  // WebSocket connection
  useEffect(() => {
    wsClient.connect().catch(console.error)

    // Handle WebSocket events
    const handleAudioResponse = (message: WebSocketMessage) => {
      const data = message.data as { answer?: string; audio_base64?: string; audio_url?: string }
      
      if (data.answer) {
        // Add AI response to commentary
        const aiItem: CommentaryItem = {
          id: `ai-${Date.now()}`,
          type: 'analysis',
          timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
          content: data.answer
        }
        setCommentary(prev => [aiItem, ...prev.slice(0, settings.maxCommentaryItems - 1)])
      }

      // Play audio response if available
      if (data.audio_base64) {
        playAudioBase64(data.audio_base64)
      } else if (data.audio_url) {
        playAudioUrl(data.audio_url)
      }

      setIsNarrating(false)
      setIsProcessing(false)
    }

    const handlePauseVideo = () => {
      setShouldPause(true)
      // Reset after a short delay
      setTimeout(() => setShouldPause(false), 100)
    }

    const handleProcessingStart = () => {
      setIsProcessing(true)
      setIsNarrating(true)
    }

    const handleProcessingComplete = () => {
      setIsProcessing(false)
    }

    const handleError = (message: WebSocketMessage) => {
      const data = message.data as { message?: string }
      console.error('WebSocket error:', data.message)

      const errorItem: CommentaryItem = {
        id: `error-${Date.now()}`,
        type: 'analysis',
        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
        content: `I encountered an issue: ${data.message || 'Unknown error'}. Please try again.`
      }
      setCommentary(prev => [errorItem, ...prev.slice(0, settings.maxCommentaryItems - 1)])
      setIsProcessing(false)
      setIsNarrating(false)
    }

    const handlePushCommentary = (message: WebSocketMessage) => {
      const data = message.data as CommentaryItem

      console.log('Received pushed commentary:', data)

      // Add to commentary feed
      setCommentary(prev => [data, ...prev.slice(0, settings.maxCommentaryItems - 1)])
    }

    const handleEventUpdate = (message: WebSocketMessage) => {
      const data = message.data

      console.log('Received event update:', data)

      // Update event data with new values
      setEventData(prev => ({
        ...prev,
        ...data
      }))
    }

    wsClient.on('AUDIO_RESPONSE', handleAudioResponse)
    wsClient.on('PAUSE_VIDEO', handlePauseVideo)
    wsClient.on('PROCESSING_START', handleProcessingStart)
    wsClient.on('PROCESSING_COMPLETE', handleProcessingComplete)
    wsClient.on('ERROR', handleError)
    wsClient.on('PUSH_COMMENTARY', handlePushCommentary)
    wsClient.on('PUSH_EVENT_UPDATE', handleEventUpdate)

    return () => {
      wsClient.off('AUDIO_RESPONSE', handleAudioResponse)
      wsClient.off('PAUSE_VIDEO', handlePauseVideo)
      wsClient.off('PROCESSING_START', handleProcessingStart)
      wsClient.off('PROCESSING_COMPLETE', handleProcessingComplete)
      wsClient.off('ERROR', handleError)
      wsClient.off('PUSH_COMMENTARY', handlePushCommentary)
      wsClient.off('PUSH_EVENT_UPDATE', handleEventUpdate)
      wsClient.disconnect()
    }
  }, [])

  // Audio playback helpers
  const playAudioBase64 = (base64Data: string) => {
    try {
      const audioBlob = base64ToBlob(base64Data, 'audio/mpeg')
      const audioUrl = URL.createObjectURL(audioBlob)
      
      if (audioRef.current) {
        audioRef.current.pause()
      }
      
      audioRef.current = new Audio(audioUrl)
      audioRef.current.play().catch(console.error)
      
      audioRef.current.onended = () => {
        URL.revokeObjectURL(audioUrl)
      }
    } catch (error) {
      console.error('Failed to play audio:', error)
    }
  }

  const playAudioUrl = (url: string) => {
    console.log('Playing audio from URL:', url)
    
    // Construct full URL if relative
    const fullUrl = url.startsWith('http') ? url : `http://localhost:8000${url}`
    console.log('Full audio URL:', fullUrl)
    
    // Use the DOM audio element for better browser compatibility
    if (audioRef.current) {
      audioRef.current.src = fullUrl
      audioRef.current.load()
      
      // Mute video while AI audio plays
      setIsPlayingAIAudio(true)
      
      audioRef.current.onended = () => {
        setIsPlayingAIAudio(false)
      }
      
      audioRef.current.onerror = () => {
        setIsPlayingAIAudio(false)
      }
      
      audioRef.current.play()
        .then(() => console.log('Audio playing successfully'))
        .catch((error) => {
          console.error('Audio play failed:', error)
          setIsPlayingAIAudio(false)
          // Some browsers block autoplay - show a message
          if (error.name === 'NotAllowedError') {
            console.log('Autoplay blocked by browser. User interaction required.')
          }
        })
    } else {
      console.error('Audio element not found')
    }
  }

  const base64ToBlob = (base64: string, mimeType: string): Blob => {
    const byteCharacters = atob(base64)
    const byteNumbers = new Array(byteCharacters.length)
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i)
    }
    const byteArray = new Uint8Array(byteNumbers)
    return new Blob([byteArray], { type: mimeType })
  }

  // Handle screen capture setup
  const handleStartScreenCapture = useCallback(async () => {
    const success = await startPersistentScreenCapture()
    if (success) {
      setScreenCaptureActive(true)
      setShowScreenCapturePrompt(false)

      // Add status message
      const statusItem: CommentaryItem = {
        id: `screen-capture-${Date.now()}`,
        type: 'analysis',
        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
        content: '📸 Screen capture enabled! I can now see what\'s happening in the video. Select the YouTube tab when prompted.'
      }
      setCommentary(prev => [statusItem, ...prev.slice(0, settings.maxCommentaryItems - 1)])
    } else {
      const errorItem: CommentaryItem = {
        id: `screen-capture-error-${Date.now()}`,
        type: 'analysis',
        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
        content: '❌ Screen capture permission denied. I\'ll work without screenshots using transcript and metadata.'
      }
      setCommentary(prev => [errorItem, ...prev.slice(0, settings.maxCommentaryItems - 1)])
      setShowScreenCapturePrompt(false)
    }
  }, [settings.maxCommentaryItems])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (isScreenCaptureActive()) {
        stopPersistentScreenCapture()
      }
    }
  }, [])

  // Handle video load
  const handleVideoLoaded = useCallback((response: VideoLoadResponse) => {
    setVideoId(response.video_id)
    setIsLive(response.is_live)

    // Update event data
    setEventData(prev => ({
      ...prev,
      eventName: response.title.split('-')[0]?.trim() || "Winter Olympics",
      eventSubtitle: response.title.split('-')[1]?.trim() || "Event",
      venue: response.is_live ? "Live Broadcast" : "Recorded Event",
      isLive: response.is_live
    }))

    // Add status message to commentary
    const statusItem: CommentaryItem = {
      id: `status-${Date.now()}`,
      type: 'market_shift',
      timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
      content: response.message,
      highlight: response.has_captions 
        ? { value: 'Captions Available', label: '' }
        : undefined
    }
    setCommentary(prev => [statusItem, ...prev.slice(0, settings.maxCommentaryItems - 1)])
  }, [])

  // Handle play state changes
  const handlePlayStateChange = useCallback((playing: boolean) => {
    setIsPlaying(playing)
  }, [])

  // Handle time updates from video player
  const handleTimeUpdate = useCallback((time: number) => {
    setCurrentTime(time)
    
    // Send playback update to backend (throttled)
    if (videoId && Math.floor(time) % 5 === 0) {
      wsClient.sendPlaybackUpdate(videoId, time)
    }
  }, [videoId])

  // Handle user questions via REST API
  const handleSendMessage = useCallback(async (message: string) => {
    if (!videoId) {
      // No video loaded - provide helpful message
      const helpItem: CommentaryItem = {
        id: `help-${Date.now()}`,
        type: 'analysis',
        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
        content: 'Please load a YouTube video first by pasting the URL above. Then I can answer your questions about what\'s happening in the event!'
      }
      setCommentary(prev => [helpItem, ...prev.slice(0, settings.maxCommentaryItems - 1)])
      return
    }

    // Stop any currently playing AI audio
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
      setIsPlayingAIAudio(false)
    }

    setIsProcessing(true)
    setIsNarrating(true)

    // Add user question to commentary
    const userItem: CommentaryItem = {
      id: `user-${Date.now()}`,
      type: 'analysis',
      timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
      content: `You asked: "${message}"`
    }
    setCommentary(prev => [userItem, ...prev.slice(0, settings.maxCommentaryItems - 1)])

    try {
      // Capture screenshot from persistent stream if active
      let screenshot: string | undefined = undefined

      console.log(`🔍 Screen capture check: screenCaptureActive=${screenCaptureActive}, isScreenCaptureActive()=${isScreenCaptureActive()}`)

      if (screenCaptureActive && isScreenCaptureActive()) {
        try {
          console.log('📸 Attempting to capture screenshot from persistent stream...')
          const capturedFrame = await captureFromPersistentStream()
          if (capturedFrame) {
            screenshot = capturedFrame
            console.log(`✅ Screenshot captured: ${capturedFrame.length} chars`)
          } else {
            console.log('⚠️ Screenshot capture returned null')
          }
        } catch (e) {
          console.log('⚠️ Screenshot capture failed, continuing without:', e)
        }
      } else {
        console.log('ℹ️ Screen capture not active - no screenshot will be sent')
        console.log('   To enable visual context: Click "Enable Screen Capture" button at the top')
      }

      // Use REST API for question (more reliable than WebSocket for this)
      const response = await askQuestion(message, videoId, currentTime, isLive, screenshot)

      // Add AI response to commentary
      const aiItem: CommentaryItem = {
        id: `ai-${Date.now()}`,
        type: 'analysis',
        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
        content: response.answer
      }
      setCommentary(prev => [aiItem, ...prev.slice(0, settings.maxCommentaryItems - 2)])

      // Play audio response
      if (response.audio_url) {
        playAudioUrl(response.audio_url)
      }
    } catch (error) {
      console.error('Failed to get answer:', error)
      
      const errorItem: CommentaryItem = {
        id: `error-${Date.now()}`,
        type: 'analysis',
        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
        content: 'I\'m having trouble answering right now. Please try again in a moment.'
      }
      setCommentary(prev => [errorItem, ...prev.slice(0, settings.maxCommentaryItems - 1)])
    } finally {
      setIsProcessing(false)
      setIsNarrating(false)
    }
  }, [videoId, currentTime, isLive])

  // Handle voice input with auto-pause
  const handleVoiceInput = useCallback((transcript: string) => {
    // Voice was detected and transcribed - pause the video
    setShouldPause(true)
    setTimeout(() => setShouldPause(false), 100)
    
    // Notify backend about voice detection
    wsClient.sendVoiceDetected()
    
    // Submit the question
    handleSendMessage(transcript)
  }, [handleSendMessage])

  // Handle when user starts speaking (before transcription)
  const handleVoiceStart = useCallback(() => {
    // Pause video immediately when voice is detected
    setShouldPause(true)
    setTimeout(() => setShouldPause(false), 100)
    wsClient.sendVoiceDetected()
  }, [])

  return (
    <div className="bg-black font-sans text-white min-h-screen flex flex-col overflow-hidden relative">
      {/* Hidden audio element for TTS playback */}
      <audio ref={audioRef} className="hidden" />

      {/* Video Background with Controls */}
      <VideoPlayer 
        videoId={videoId || undefined}
        onPlayStateChange={handlePlayStateChange}
        onTimeUpdate={handleTimeUpdate}
        isNarrating={isNarrating}
        externalPause={shouldPause}
        voiceInputActive={isListeningToVoice}
        aiSpeaking={isPlayingAIAudio}
      />

      {/* Header */}
      <StreamHeader />

      {/* Screen Capture Status Indicator */}
      {videoId && (
        screenCaptureActive ? (
          <div className="fixed top-24 right-4 z-50 bg-green-500/20 backdrop-blur-xl border border-green-500/30 rounded-full px-4 py-2 flex items-center gap-2 text-sm">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="text-green-100">Screen Capture Active</span>
          </div>
        ) : !showScreenCapturePrompt && (
          <div className="fixed top-24 right-4 z-50 bg-yellow-500/20 backdrop-blur-xl border border-yellow-500/30 rounded-full px-4 py-2 flex items-center gap-2 text-sm cursor-pointer hover:bg-yellow-500/30 transition-colors"
               onClick={() => setShowScreenCapturePrompt(true)}>
            <div className="w-2 h-2 bg-yellow-400 rounded-full" />
            <span className="text-yellow-100">Visual context disabled</span>
            <span className="text-yellow-200 text-xs ml-1">(click to enable)</span>
          </div>
        )
      )}

      {/* Main Content - pointer-events-none to allow clicking video, children have pointer-events-auto */}
      <main className="relative z-10 flex-1 flex flex-col lg:flex-row px-4 lg:px-12 pt-20 lg:pt-28 pb-40 lg:pb-32 gap-4 lg:gap-8 h-full overflow-y-auto pointer-events-none">
        {/* Left Sidebar - Event Info */}
        <div className="pointer-events-auto">
          <EventSidebar {...eventData} />
        </div>

        {/* Center spacer */}
        <div className="hidden lg:flex flex-1" />

        {/* Right Sidebar - AI Commentary */}
        <div className="pointer-events-auto">
          <AICommentary items={commentary} isLive={isPlaying} />
        </div>
      </main>

      {/* Screen Capture Prompt - Shown once at start */}
      {showScreenCapturePrompt && !screenCaptureActive && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 w-full max-w-2xl px-4 z-50">
          <div className="bg-lavender-500/10 backdrop-blur-xl border border-lavender-500/20 rounded-2xl p-4 shadow-xl">
            <div className="flex items-start gap-4">
              <div className="text-3xl">📸</div>
              <div className="flex-1">
                <h3 className="font-semibold text-white mb-1">Enable Visual Context</h3>
                <p className="text-sm text-white/70 mb-3">
                  Let me see what's happening in the video for better answers.
                  You'll be asked once to select the YouTube tab to share.
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={handleStartScreenCapture}
                    className="px-4 py-2 bg-lavender-500 hover:bg-lavender-600 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    Enable Screen Capture
                  </button>
                  <button
                    onClick={() => setShowScreenCapturePrompt(false)}
                    className="px-4 py-2 bg-white/5 hover:bg-white/10 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    Skip (Use Transcript Only)
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Video URL Input - Fixed at top below header (shown when no video) */}
      {!videoId && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 w-full max-w-2xl px-4 z-40" style={{ marginTop: showScreenCapturePrompt ? '140px' : '0' }}>
          <VideoUrlInput
            onVideoLoaded={handleVideoLoaded}
            disabled={isProcessing}
          />
        </div>
      )}

      {/* Suggested Prompts */}
      <div className="fixed bottom-24 lg:bottom-28 left-1/2 -translate-x-1/2 w-full max-w-3xl z-40 px-4 lg:px-6">
        <SuggestedPrompts
          onSelectPrompt={handleSendMessage}
          videoLoaded={!!videoId}
          isProcessing={isProcessing}
        />
      </div>

      {/* AI Chat Input */}
      <AIChatInput
        onSendMessage={handleSendMessage}
        onVoiceInput={handleVoiceInput}
        onListeningChange={setIsListeningToVoice}
        isProcessing={isProcessing}
        placeholder={videoId
          ? "Ask about the event, rules, athletes, or what's happening..."
          : "Load a video first, then ask questions..."}
      />

      {/* Accessibility: Screen reader announcements */}
      <div className="sr-only" role="status" aria-live="polite">
        {isProcessing && "AI is processing your question..."}
        {isNarrating && "AI is responding..."}
      </div>
    </div>
  )
}
