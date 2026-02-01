"use client"

import { Sparkles } from "lucide-react"

interface SuggestedPromptsProps {
  onSelectPrompt: (prompt: string) => void
  videoLoaded: boolean
  isProcessing: boolean
}

const DEFAULT_PROMPTS = [
  "Who's playing right now?",
  "What's happening in the event?",
  "Tell me about the athletes"
]

const VIDEO_LOADED_PROMPTS = [
  "Who are the competitors?",
  "What's the current score?",
  "Tell me about this event",
  "Who's favored to win?"
]

export function SuggestedPrompts({ onSelectPrompt, videoLoaded, isProcessing }: SuggestedPromptsProps) {
  const prompts = videoLoaded ? VIDEO_LOADED_PROMPTS : DEFAULT_PROMPTS

  if (isProcessing) {
    return null // Hide during processing
  }

  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-hide">
      <div className="flex items-center gap-1 text-white/40 text-xs shrink-0">
        <Sparkles className="size-3" />
        <span>Try:</span>
      </div>
      <div className="flex gap-2">
        {prompts.map((prompt, index) => (
          <button
            key={index}
            onClick={() => onSelectPrompt(prompt)}
            className="px-3 py-1.5 rounded-full text-xs text-white/70 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-lavender-400/30 transition-all whitespace-nowrap"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  )
}
