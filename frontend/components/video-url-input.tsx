"use client"

import React, { useState, useCallback } from "react"
import { Link2, Loader2, AlertCircle, CheckCircle2 } from "lucide-react"
import { loadVideo, VideoLoadResponse } from "@/lib/api"
import { extractVideoId } from "@/lib/youtube"

interface VideoUrlInputProps {
  onVideoLoaded: (response: VideoLoadResponse) => void
  disabled?: boolean
}

export function VideoUrlInput({ onVideoLoaded, disabled = false }: VideoUrlInputProps) {
  const [url, setUrl] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!url.trim()) {
      setError("Please enter a YouTube URL")
      return
    }

    // Validate URL format
    const videoId = extractVideoId(url.trim())
    if (!videoId) {
      setError("Invalid YouTube URL. Please enter a valid video or livestream URL.")
      return
    }

    setIsLoading(true)
    setError(null)
    setSuccess(null)

    try {
      const response = await loadVideo(url.trim())
      setSuccess(response.message)
      onVideoLoaded(response)
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load video")
    } finally {
      setIsLoading(false)
    }
  }, [url, onVideoLoaded])

  const handlePaste = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText()
      if (text) {
        setUrl(text)
        setError(null)
      }
    } catch {
      // Clipboard access denied - do nothing
    }
  }, [])

  return (
    <div className="w-full max-w-2xl mx-auto">
      <form onSubmit={handleSubmit} className="relative">
        <div className="input-glass p-2 rounded-xl lg:rounded-2xl flex items-center gap-2 lg:gap-3 shadow-2xl">
          <div className="flex-1 flex items-center gap-2 lg:gap-3 px-3 lg:px-4">
            <Link2 className="size-4 lg:size-5 text-lavender-300 flex-shrink-0" />
            <input
              type="text"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value)
                setError(null)
              }}
              className="w-full bg-transparent border-none text-white placeholder-white/40 focus:ring-0 focus:outline-none text-sm py-2 lg:py-3"
              placeholder="Paste YouTube video or livestream URL..."
              disabled={disabled || isLoading}
              aria-label="YouTube video URL"
              aria-describedby={error ? "url-error" : undefined}
            />
          </div>
          <div className="flex items-center gap-1 lg:gap-2 pr-1 lg:pr-2">
            <button
              type="button"
              onClick={handlePaste}
              disabled={disabled || isLoading}
              className="hidden sm:block px-3 lg:px-4 py-2 hover:bg-white/5 rounded-lg lg:rounded-xl text-[10px] lg:text-[11px] font-semibold text-white/60 transition-colors disabled:opacity-50"
              aria-label="Paste from clipboard"
            >
              Paste
            </button>
            <button
              type="submit"
              disabled={disabled || isLoading || !url.trim()}
              className="size-9 lg:size-11 bg-lavender-500 hover:bg-lavender-600 disabled:bg-lavender-500/50 disabled:cursor-not-allowed text-white rounded-lg lg:rounded-xl flex items-center justify-center transition-all shadow-lg"
              aria-label="Load video"
            >
              {isLoading ? (
                <Loader2 className="size-4 lg:size-5 animate-spin" />
              ) : (
                <Link2 className="size-4 lg:size-5" />
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Status Messages */}
      {error && (
        <div 
          id="url-error"
          className="mt-3 flex items-center gap-2 text-red-400 text-sm"
          role="alert"
        >
          <AlertCircle className="size-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
      
      {success && (
        <div 
          className="mt-3 flex items-center gap-2 text-emerald-400 text-sm"
          role="status"
        >
          <CheckCircle2 className="size-4 flex-shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {/* Helper Text */}
      <p className="mt-3 text-center text-[10px] font-bold uppercase tracking-widest text-white/40">
        Supports YouTube videos and livestreams
      </p>
    </div>
  )
}
