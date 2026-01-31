"use client"

import React, { useState, useRef, useEffect, useCallback } from "react"
import { MessageSquare, Wand2, Mic, MicOff, Loader2 } from "lucide-react"

interface AIChatInputProps {
  onSendMessage: (message: string) => void
  onVoiceInput?: (transcript: string) => void
  onVoiceStart?: () => void  // Called when voice detection starts
  isProcessing?: boolean
  placeholder?: string
}

export function AIChatInput({ 
  onSendMessage, 
  onVoiceInput,
  onVoiceStart,
  isProcessing = false,
  placeholder = "Ask AI about historical comparisons or live stats..."
}: AIChatInputProps) {
  const [message, setMessage] = useState("")
  const [isListening, setIsListening] = useState(false)
  const [interimTranscript, setInterimTranscript] = useState("")
  const recognitionRef = useRef<SpeechRecognition | null>(null)

  useEffect(() => {
    // Check for browser support
    if (typeof window !== 'undefined' && ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) {
      const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition
      recognitionRef.current = new SpeechRecognitionAPI()
      recognitionRef.current.continuous = false
      recognitionRef.current.interimResults = true  // Enable interim results for better UX
      recognitionRef.current.lang = 'en-US'

      recognitionRef.current.onstart = () => {
        // Notify parent that voice detection has started
        onVoiceStart?.()
      }

      recognitionRef.current.onresult = (event) => {
        let finalTranscript = ""
        let interim = ""

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript
          if (event.results[i].isFinal) {
            finalTranscript += transcript
          } else {
            interim += transcript
          }
        }

        setInterimTranscript(interim)

        if (finalTranscript) {
          setMessage(finalTranscript)
          setInterimTranscript("")
          if (onVoiceInput) {
            onVoiceInput(finalTranscript)
          }
          setIsListening(false)
        }
      }

      recognitionRef.current.onerror = (event) => {
        // "aborted" is expected when user stops listening - not an error
        if (event.error !== 'aborted') {
          console.error('Speech recognition error:', event.error)
        }
        setIsListening(false)
        setInterimTranscript("")
        
        // Announce error to screen readers
        if (event.error === 'not-allowed') {
          alert('Microphone access was denied. Please enable microphone permissions to use voice input.')
        }
      }

      recognitionRef.current.onend = () => {
        setIsListening(false)
        setInterimTranscript("")
      }
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort()
      }
    }
  }, [onVoiceInput, onVoiceStart])

  const toggleVoiceInput = useCallback(() => {
    if (!recognitionRef.current) {
      alert("Voice input is not supported in your browser. Please try Chrome, Edge, or Safari.")
      return
    }

    if (isListening) {
      recognitionRef.current.stop()
      setIsListening(false)
      setInterimTranscript("")
    } else {
      try {
        recognitionRef.current.start()
        setIsListening(true)
      } catch (error) {
        console.error('Failed to start speech recognition:', error)
        setIsListening(false)
      }
    }
  }, [isListening])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (message.trim() && !isProcessing) {
      onSendMessage(message.trim())
      setMessage("")
    }
  }

  const handleQuickAction = (action: string) => {
    onSendMessage(action)
  }

  return (
    <div className="fixed bottom-6 lg:bottom-10 left-1/2 -translate-x-1/2 w-full max-w-3xl z-50 px-4 lg:px-6">
      <form onSubmit={handleSubmit} className="input-glass p-2 rounded-xl lg:rounded-2xl flex items-center gap-2 lg:gap-3 shadow-2xl">
        <div className="flex-1 flex items-center gap-2 lg:gap-3 px-3 lg:px-4">
          <MessageSquare className="size-4 lg:size-5 text-lavender-300 flex-shrink-0" aria-hidden="true" />
          <div className="w-full relative">
            <input 
              type="text"
              value={isListening ? interimTranscript || message : message}
              onChange={(e) => setMessage(e.target.value)}
              className="w-full bg-transparent border-none text-white placeholder-white/40 focus:ring-0 focus:outline-none text-sm py-2 lg:py-3"
              placeholder={isListening ? "Listening..." : placeholder}
              disabled={isProcessing || isListening}
              aria-label="Ask the AI a question"
            />
          </div>
        </div>
        <div className="flex items-center gap-1 lg:gap-2 pr-1 lg:pr-2">
          {/* Voice Input Button */}
          <button 
            type="button"
            onClick={toggleVoiceInput}
            disabled={isProcessing}
            className={`size-9 lg:size-11 rounded-lg lg:rounded-xl flex items-center justify-center transition-all ${
              isListening 
                ? 'bg-red-500 text-white animate-pulse' 
                : 'hover:bg-white/5 text-white/60 hover:text-white'
            } disabled:opacity-50`}
            aria-label={isListening ? "Stop listening" : "Start voice input"}
            aria-pressed={isListening}
          >
            {isListening ? (
              <MicOff className="size-4 lg:size-5" />
            ) : (
              <Mic className="size-4 lg:size-5" />
            )}
          </button>
          
          <button 
            type="button"
            onClick={() => handleQuickAction("What is happening right now in the event?")}
            disabled={isProcessing}
            className="hidden sm:block px-3 lg:px-4 py-2 hover:bg-white/5 rounded-lg lg:rounded-xl text-[10px] lg:text-[11px] font-semibold text-white/60 transition-colors disabled:opacity-50"
          >
            What's Happening?
          </button>
          
          <button 
            type="submit"
            disabled={isProcessing || (!message.trim() && !isListening)}
            className="size-9 lg:size-11 bg-lavender-500 hover:bg-lavender-600 disabled:bg-lavender-500/50 disabled:cursor-not-allowed text-white rounded-lg lg:rounded-xl flex items-center justify-center transition-all shadow-lg"
            aria-label="Send message"
          >
            {isProcessing ? (
              <Loader2 className="size-4 lg:size-5 animate-spin" />
            ) : (
              <Wand2 className="size-4 lg:size-5" />
            )}
          </button>
        </div>
      </form>
      
      {/* Quick Action Links */}
      <div className="flex flex-wrap justify-center gap-3 lg:gap-4 mt-3 lg:mt-4">
        <button 
          onClick={() => handleQuickAction("Explain the rules and scoring for this sport in simple terms")}
          disabled={isProcessing}
          className="text-[10px] font-bold uppercase tracking-widest text-white/40 hover:text-white/80 transition-colors disabled:opacity-50"
        >
          Explain Rules
        </button>
        <span className="text-white/20 hidden sm:inline">•</span>
        <button 
          onClick={() => handleQuickAction("Tell me about this athlete's background and achievements")}
          disabled={isProcessing}
          className="text-[10px] font-bold uppercase tracking-widest text-white/40 hover:text-white/80 transition-colors disabled:opacity-50"
        >
          Athlete Bio
        </button>
        <span className="text-white/20 hidden sm:inline">•</span>
        <button 
          onClick={() => handleQuickAction("Describe what just happened in an accessible way")}
          disabled={isProcessing}
          className="text-[10px] font-bold uppercase tracking-widest text-white/40 hover:text-white/80 transition-colors disabled:opacity-50"
        >
          Describe Action
        </button>
      </div>

      {/* Screen reader status */}
      <div className="sr-only" role="status" aria-live="polite">
        {isListening && "Listening for voice input..."}
        {isProcessing && "Processing your question..."}
      </div>
    </div>
  )
}

// Extend Window interface for Speech Recognition
declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition
    webkitSpeechRecognition: typeof SpeechRecognition
  }
}
