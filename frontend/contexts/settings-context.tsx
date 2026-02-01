"use client"

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export interface Settings {
  // Playback
  autoPauseOnVoice: boolean
  volumeDuckingPercent: number
  showTimerDuringPlayback: boolean

  // AI
  voiceResponseEnabled: boolean
  autoSubmitVoice: boolean
  responseVerbosity: 'concise' | 'detailed'

  // Accessibility
  highContrast: boolean
  reducedMotion: boolean

  // Commentary
  commentaryAutoScroll: boolean
  maxCommentaryItems: number
  showTimestamps: boolean
}

const defaultSettings: Settings = {
  autoPauseOnVoice: true,
  volumeDuckingPercent: 5,  // Lower to 5% for more drastic volume reduction during voice input
  showTimerDuringPlayback: false,
  voiceResponseEnabled: true,
  autoSubmitVoice: true,
  responseVerbosity: 'concise',
  highContrast: false,
  reducedMotion: false,
  commentaryAutoScroll: true,
  maxCommentaryItems: 10,
  showTimestamps: true,
}

interface SettingsContextType {
  settings: Settings
  updateSettings: (updates: Partial<Settings>) => void
  resetSettings: () => void
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined)

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(defaultSettings)
  const [isInitialized, setIsInitialized] = useState(false)

  // Load from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('winterstream-settings')
    if (saved) {
      try {
        setSettings({ ...defaultSettings, ...JSON.parse(saved) })
      } catch (e) {
        console.error('Failed to load settings:', e)
      }
    }
    setIsInitialized(true)
  }, [])

  // Save to localStorage on change (skip initial load)
  useEffect(() => {
    if (isInitialized) {
      localStorage.setItem('winterstream-settings', JSON.stringify(settings))
    }
  }, [settings, isInitialized])

  const updateSettings = (updates: Partial<Settings>) => {
    setSettings(prev => ({ ...prev, ...updates }))
  }

  const resetSettings = () => {
    setSettings(defaultSettings)
  }

  return (
    <SettingsContext.Provider value={{ settings, updateSettings, resetSettings }}>
      {children}
    </SettingsContext.Provider>
  )
}

export function useSettings() {
  const context = useContext(SettingsContext)
  if (!context) {
    throw new Error('useSettings must be used within SettingsProvider')
  }
  return context
}
