"use client"

import React from "react"
import SpeechRecognition from "speech-recognition"

import { useState, useRef, useEffect } from "react"
import { MessageSquare, Wand2, Mic, MicOff, Loader2 } from "lucide-react"

interface AIChatInputProps {
  onSendMessage: (message: string) => void
  onVoiceInput?: (transcript: string) => void
  isProcessing?: boolean
  placeholder?: string
}

export function AIChatInput({ 
  onSendMessage, 
  onVoiceInput,
  isProcessing = false,
  placeholder = "Ask AI about historical comparisons or live stats..."
}: AIChatInputProps) {
  const [message, setMessage] = useState("")
  const [isListening, setIsListening] = useState(false)
  const recognitionRef = useRef<SpeechRecognition | null>(null)

  useEffect(() => {
    // Check for browser support
    if (typeof window !== 'undefined' && ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) {
      const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition
      recognitionRef.current = new SpeechRecognitionAPI()
      recognitionRef.current.continuous = false
      recognitionRef.current.interimResults = false
      recognitionRef.current.lang = 'en-US'

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript
        setMessage(transcript)
        if (onVoiceInput) {
          onVoiceInput(transcript)
        }
        setIsListening(false)
      }

      recognitionRef.current.onerror = () => {
        setIsListening(false)
      }

      recognitionRef.current.onend = () => {
        setIsListening(false)
      }
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort()
      }
    }
  }, [onVoiceInput])

  const toggleVoiceInput = () => {
    if (!recognitionRef.current) {
      alert("Voice input is not supported in your browser")
      return
    }

    if (isListening) {
      recognitionRef.current.stop()
      setIsListening(false)
    } else {
      recognitionRef.current.start()
      setIsListening(true)
    }
  }

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
          <MessageSquare className="size-4 lg:size-5 text-lavender-300 flex-shrink-0" />
          <input 
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            className="w-full bg-transparent border-none text-white placeholder-white/40 focus:ring-0 focus:outline-none text-sm py-2 lg:py-3"
            placeholder={placeholder}
            disabled={isProcessing}
            aria-label="Ask the AI a question"
          />
        </div>
        <div className="flex items-center gap-1 lg:gap-2 pr-1 lg:pr-2">
          {/* Voice Input Button */}
          <button 
            type="button"
            onClick={toggleVoiceInput}
            className={`size-9 lg:size-11 rounded-lg lg:rounded-xl flex items-center justify-center transition-all ${
              isListening 
                ? 'bg-red-500 text-white animate-pulse' 
                : 'hover:bg-white/5 text-white/60 hover:text-white'
            }`}
            aria-label={isListening ? "Stop listening" : "Start voice input"}
          >
            {isListening ? (
              <MicOff className="size-4 lg:size-5" />
            ) : (
              <Mic className="size-4 lg:size-5" />
            )}
          </button>
          
          <button 
            type="button"
            onClick={() => handleQuickAction("Compare current stats with historical records")}
            className="hidden sm:block px-3 lg:px-4 py-2 hover:bg-white/5 rounded-lg lg:rounded-xl text-[10px] lg:text-[11px] font-semibold text-white/60 transition-colors"
          >
            Compare Stats
          </button>
          
          <button 
            type="submit"
            disabled={isProcessing || !message.trim()}
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
      <div className="flex justify-center gap-3 lg:gap-4 mt-3 lg:mt-4">
        <button 
          onClick={() => handleQuickAction("Explain the technical rules for this event")}
          className="text-[10px] font-bold uppercase tracking-widest text-white/40 hover:text-white/80 transition-colors"
        >
          Technical Rules
        </button>
        <span className="text-white/20">•</span>
        <button 
          onClick={() => handleQuickAction("Tell me about this athlete's background")}
          className="text-[10px] font-bold uppercase tracking-widest text-white/40 hover:text-white/80 transition-colors"
        >
          Athlete Bio
        </button>
        <span className="text-white/20">•</span>
        <button 
          onClick={() => handleQuickAction("What is the medal history for this event?")}
          className="text-[10px] font-bold uppercase tracking-widest text-white/40 hover:text-white/80 transition-colors"
        >
          Medal History
        </button>
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
