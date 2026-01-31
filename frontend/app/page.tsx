"use client"

import { useState, useCallback, useRef, useEffect } from "react"
import { StreamHeader } from "@/components/stream-header"
import { EventSidebar } from "@/components/event-sidebar"
import { AICommentary, type CommentaryItem } from "@/components/ai-commentary"
import { AIChatInput } from "@/components/ai-chat-input"
import { VideoPlayer } from "@/components/video-player"

// Simulated narration phrases for demo
const NARRATION_PHRASES = [
  "The skater glides gracefully across the ice, preparing for the next element.",
  "A beautiful triple axel! The crowd erupts in applause.",
  "Moving into the footwork sequence now, showing incredible edge control.",
  "The music swells as she approaches center ice for the combination spin.",
  "Flawless execution on that jump. The technical panel will be pleased.",
  "She's maintaining excellent posture throughout this challenging choreography.",
  "The spiral sequence showcases her flexibility and artistry.",
  "A slight wobble on the landing, but she recovers beautifully.",
  "The performance is building to its climactic finale.",
  "What a stunning layback spin to close out this remarkable program!"
]

// Simulated AI responses for Q&A
const AI_RESPONSES: Record<string, string> = {
  "technical rules": "In figure skating, the Technical Element Score (TES) is calculated by adding the base values of each element performed, plus Grade of Execution (GOE) adjustments. Elements include jumps, spins, step sequences, and lifts. Each element has a specific base value, and judges can add or subtract up to 5 points based on quality.",
  "athlete bio": "The current skater is a two-time World Championship medalist, known for her exceptional artistry and technical prowess. She began skating at age 4 and has won 15 international medals throughout her career. Her signature move is the triple-triple combination jump.",
  "medal history": "This event has been part of the Olympics since 1908. Notable champions include Sonja Henie (3 gold medals), Katarina Witt (2 golds), and Yuna Kim (gold in 2010). The current record for highest score in the free skate is 158.44 points.",
  "compare stats": "Current performance is tracking 6.2% above the skater's season average. Her jump success rate today is 94% compared to her typical 89%. The artistic components are scoring 0.8 points higher than her personal best.",
  "score": "The current score projection is 84.25 TES with an estimated 74.5 PCS, for a total of approximately 158.75 points.",
  "who": "The current performer is representing her national federation in the Women's Free Skate event. She is the reigning national champion and a strong medal contender.",
  "default": "Based on my analysis of the current performance, I'm seeing excellent technical execution and strong artistic interpretation. The skater is performing at a very high level today."
}

export default function SportsNarratorPage() {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isNarrating, setIsNarrating] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [commentary, setCommentary] = useState<CommentaryItem[]>([
    {
      id: '1',
      type: 'market_shift',
      timestamp: '12:08:45',
      content: 'Gold probability spiked after that Triple Axel. Execution score is currently trending at',
      highlight: { value: '94.1%', label: 'accuracy.' }
    },
    {
      id: '2',
      type: 'historical',
      timestamp: '12:07:20',
      title: 'Versus 2018 Pace',
      content: '',
      comparison: {
        current: 84.25,
        record: 78.30,
        note: 'Pacing 5.95 points above the 2010 Olympic baseline.'
      }
    },
    {
      id: '3',
      type: 'analysis',
      timestamp: '12:06:10',
      content: 'The artistic components are showing remarkable depth. We\'re seeing scores that could potentially set a new personal season best.'
    }
  ])

  const [eventData] = useState({
    eventName: "Figure Skating",
    eventSubtitle: "Women's Free",
    venue: "Beijing Capital Stadium",
    isLive: true,
    winProbability: 74.2,
    probabilityChange: 2.4,
    technicalScore: 84.25,
    riskWarning: {
      title: "Upcoming Risk",
      description: "Triple Lutz-Triple Toe combination approaching. AI predicts a ",
      probability: 12
    }
  })

  const narrationIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const speechSynthesisRef = useRef<SpeechSynthesisUtterance | null>(null)

  // Text-to-speech for narration
  const speak = useCallback((text: string) => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      // Cancel any ongoing speech
      window.speechSynthesis.cancel()
      
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.rate = 0.95
      utterance.pitch = 1
      utterance.volume = 0.8
      
      // Try to find a good voice
      const voices = window.speechSynthesis.getVoices()
      const preferredVoice = voices.find(v => 
        v.name.includes('Google') || v.name.includes('Microsoft') || v.name.includes('Samantha')
      )
      if (preferredVoice) {
        utterance.voice = preferredVoice
      }
      
      speechSynthesisRef.current = utterance
      window.speechSynthesis.speak(utterance)
    }
  }, [])

  // Handle play state changes
  const handlePlayStateChange = useCallback((playing: boolean) => {
    setIsPlaying(playing)
    
    if (playing) {
      // Start narration cycle
      setIsNarrating(true)
      
      // Immediate first narration
      const firstPhrase = NARRATION_PHRASES[Math.floor(Math.random() * NARRATION_PHRASES.length)]
      speak(firstPhrase)
      
      // Add to commentary
      const newItem: CommentaryItem = {
        id: Date.now().toString(),
        type: 'narration',
        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
        content: firstPhrase
      }
      setCommentary(prev => [newItem, ...prev])
      
      // Continue narrating every 8-15 seconds
      narrationIntervalRef.current = setInterval(() => {
        const phrase = NARRATION_PHRASES[Math.floor(Math.random() * NARRATION_PHRASES.length)]
        speak(phrase)
        
        const item: CommentaryItem = {
          id: Date.now().toString(),
          type: 'narration',
          timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
          content: phrase
        }
        setCommentary(prev => [item, ...prev.slice(0, 9)])
      }, 8000 + Math.random() * 7000)
      
    } else {
      // Stop narration
      setIsNarrating(false)
      if (narrationIntervalRef.current) {
        clearInterval(narrationIntervalRef.current)
        narrationIntervalRef.current = null
      }
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel()
      }
    }
  }, [speak])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (narrationIntervalRef.current) {
        clearInterval(narrationIntervalRef.current)
      }
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel()
      }
    }
  }, [])

  // Handle user questions
  const handleSendMessage = useCallback((message: string) => {
    setIsProcessing(true)
    
    // Pause narration briefly to respond
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel()
    }
    
    // Simulate AI processing time
    setTimeout(() => {
      // Find matching response based on keywords
      const lowerMessage = message.toLowerCase()
      let response = AI_RESPONSES.default
      
      if (lowerMessage.includes('rule') || lowerMessage.includes('technical')) {
        response = AI_RESPONSES['technical rules']
      } else if (lowerMessage.includes('athlete') || lowerMessage.includes('bio') || lowerMessage.includes('background')) {
        response = AI_RESPONSES['athlete bio']
      } else if (lowerMessage.includes('medal') || lowerMessage.includes('history')) {
        response = AI_RESPONSES['medal history']
      } else if (lowerMessage.includes('compare') || lowerMessage.includes('stat')) {
        response = AI_RESPONSES['compare stats']
      } else if (lowerMessage.includes('score') || lowerMessage.includes('point')) {
        response = AI_RESPONSES.score
      } else if (lowerMessage.includes('who')) {
        response = AI_RESPONSES.who
      }
      
      // Speak the response
      speak(response)
      
      // Add user question and AI response to commentary
      const userItem: CommentaryItem = {
        id: `user-${Date.now()}`,
        type: 'analysis',
        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
        content: `User asked: "${message}"`
      }
      
      const aiItem: CommentaryItem = {
        id: `ai-${Date.now()}`,
        type: 'analysis',
        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
        content: response
      }
      
      setCommentary(prev => [aiItem, userItem, ...prev.slice(0, 7)])
      setIsProcessing(false)
    }, 1500)
  }, [speak])

  // Handle voice input (same as text for now)
  const handleVoiceInput = useCallback((transcript: string) => {
    // Auto-submit voice input
    handleSendMessage(transcript)
  }, [handleSendMessage])

  return (
    <div className="bg-black font-sans text-white min-h-screen flex flex-col overflow-hidden relative">
      {/* Video Background with Controls */}
      <VideoPlayer 
        onPlayStateChange={handlePlayStateChange}
        isNarrating={isNarrating}
      />

      {/* Header */}
      <StreamHeader />

      {/* Main Content */}
      <main className="relative z-10 flex-1 flex flex-col lg:flex-row px-4 lg:px-12 pt-20 lg:pt-28 pb-40 lg:pb-32 gap-4 lg:gap-8 h-full overflow-y-auto">
        {/* Left Sidebar - Event Info */}
        <EventSidebar {...eventData} />

        {/* Center - Video Area (handled by VideoPlayer component) */}
        <div className="hidden lg:flex flex-1 items-center justify-center pointer-events-none">
          {/* Play button is rendered by VideoPlayer */}
        </div>

        {/* Right Sidebar - AI Commentary */}
        <AICommentary items={commentary} isLive={isPlaying} />
      </main>

      {/* AI Chat Input */}
      <AIChatInput 
        onSendMessage={handleSendMessage}
        onVoiceInput={handleVoiceInput}
        isProcessing={isProcessing}
      />
    </div>
  )
}
